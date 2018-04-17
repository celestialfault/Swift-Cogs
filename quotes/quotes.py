from pathlib import Path
from random import randint
from typing import Sequence

import discord
from discord.ext import commands

from redbot.core import RedContext, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import warning, error

from cog_shared.odinair_libs import (
    fmt, tick, chunks, trim_to, ReactMenu, PostMenuAction,
    prompt, ConfirmMenu, PaginateMenu
)

from quotes.quote import Quote, conf, i18n, QuoteRevision
from quotes.v2_import import import_v2_data


class Quotes:
    """Save and retrieve quotes"""

    __author__ = "odinair <odinair@odinair.xyz>"

    DELETE_WARNING = i18n(
        "\N{HEAVY EXCLAMATION MARK SYMBOL} Are you sure you want to delete this quote?\n\n"
        "Unless you have a time machine, this action **cannot be undone**."
    )

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = conf
        Quote.bot = self.bot

    @commands.group(name="quote", aliases=["quotes"], invoke_without_command=True)
    @commands.guild_only()
    async def quote(self, ctx: RedContext, quote: int = None):
        """Save and retrieve quotes

        If no quote is given, a random quote is retrieved instead.
        """
        if quote is None:
            quotes = len(await self.config.guild(ctx.guild).quotes())
            if not quotes:
                await ctx.send_help()
                return
            quote = randint(1, quotes)
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(i18n("That quote doesn't exist")))
            return
        await ctx.send(embed=quote.embed)

    @quote.command(hidden=True, name="v2_import")
    @checks.is_owner()
    async def quote_v2_import(self, ctx: RedContext, path: str):
        """Import quotes data from a Red v2 instance"""
        path = Path(path) / "data" / "quotes" / "quotes.json"
        if not path.is_file():
            await ctx.send(error(i18n("That file path doesn't seem to be valid")))
            return
        async with ctx.typing():
            await import_v2_data(config=self.config, path=path)
        await ctx.send(tick(i18n("Imported data successfully.")))

    @quote.command(name="add")
    async def quote_add(self, ctx: RedContext, *, message: str):
        """Add a quote"""
        quote = await Quote.create(message, ctx.author, ctx.author)
        await ctx.send(tick(i18n("Quote added")), embed=quote.embed)

    @quote.command(name="message")
    async def quote_message(self, ctx: RedContext, message: int):
        """Quote a message by it's ID

        The message specified must be in the same channel this command is executed in

        You can obtain a message's ID by enabling Developer Mode in your Appearance settings,
        and clicking Copy ID in the message's context menu
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            await ctx.send(warning(i18n("I couldn't find that message. (is it in a different channel?)")))
        except discord.Forbidden:
            await ctx.send(warning(i18n("I'm not allowed to retrieve that message")))
        else:
            quote = await Quote.create(message.content, ctx.author, message.author)
            await ctx.send(tick(i18n("Quote added")), embed=quote.embed)

    @quote.command(name="edit", aliases=["modify"])
    async def quote_edit(self, ctx: RedContext, quote: int):
        """Interactive quote editor

        This requires you to be the quote creator, the attributed author
        or a guild moderator or administrator.
        """
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(i18n("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(i18n("You aren't authorized to modify that quote")))
            return

        desc = i18n(
            "What action(s) would you like to take?\n\n"
            "\N{BUST IN SILHOUETTE} \N{EM DASH} Attribute quote\n"
            "\N{BUSTS IN SILHOUETTE} \N{EM DASH} Change quote creator\n"
            "\N{MEMO} \N{EM DASH} Edit content\n"
            "\N{WASTEBASKET} \N{EM DASH} Delete quote\n"
            "\N{CROSS MARK} \N{EM DASH} Cancel"
        )

        embed = discord.Embed(title=i18n("Edit Quote"), description=desc)

        actions = {
            "attribute": "\N{BUST IN SILHOUETTE}",
            "creator": "\N{BUSTS IN SILHOUETTE}",
            "edit_content": "\N{MEMO}",
            "delete": "\N{WASTEBASKET}",
            "cancel": "\N{CROSS MARK}"
        }

        async def prompt_member():
            msg_ = await prompt(ctx, content=i18n("Who would you like to attribute this quote to?"), timeout=30.0,
                                delete_messages=True)
            if not msg_:
                return None
            try:
                member = await commands.MemberConverter().convert(ctx, msg_.content)
            except commands.BadArgument:
                await ctx.send(warning(i18n("Failed to convert `{}` into a member - try again?")
                                       .format(msg_.content)),
                               delete_after=30.0)
                return None
            else:
                return member

        menu = ReactMenu(ctx=ctx, actions=actions, embed=embed, post_action=PostMenuAction.DELETE)
        while True:
            async with menu as result:
                if result.timed_out or result == "cancel":
                    break

                elif result == "attribute":
                    attribute_to = await prompt_member()
                    if not attribute_to:
                        continue
                    quote.edited = True
                    quote.message_author = attribute_to
                    await quote.save()
                    await ctx.send(tick(i18n("Attributed quote to **{}**.").format(str(attribute_to))))

                elif result == "creator":
                    can_change_creator = any([
                        ctx.author == quote.creator,
                        await self.bot.is_mod(ctx.author),
                        await self.bot.is_owner(ctx.author)
                    ])
                    if not can_change_creator:
                        await ctx.send(error(i18n("You are not authorized to change the quote creator")),
                                       delete_after=30.0)
                        continue
                    attribute_to = await prompt_member()
                    if not attribute_to:
                        continue
                    quote.creator = attribute_to
                    await quote.save()
                    await ctx.send(tick(i18n("Changed quote creator to **{}**.").format(attribute_to)))

                elif result == "edit_content":
                    msg = await prompt(ctx, content=i18n("Please enter the new content for the quote"), timeout=120.0,
                                       delete_messages=True)
                    if not msg:
                        continue

                    quote.edited = True
                    quote.text = msg.content
                    await quote.save()
                    await ctx.send(tick(i18n("Modified quote contents successfully.")))

                elif result == "delete":
                    if await ConfirmMenu(ctx, content=self.DELETE_WARNING).prompt():
                        await quote.delete()
                        await ctx.send(tick(i18n("Quote successfully deleted.")), delete_after=30.0)
                        break

        try:
            await result.message.delete()
        except (discord.HTTPException, AttributeError):
            pass

    @quote.command(name="history", aliases=["revisions"])
    async def quote_history(self, ctx: RedContext, quote: int, revision: int = None):
        """Retrieve the revision history for a quote"""
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(i18n("That quote doesn't exist")))
            return
        if not quote.revisions:
            await ctx.send(warning(i18n("That quote has no recorded modifications")))
            return

        if revision is not None and 0 < revision <= len(quote.revisions):
            await ctx.send(embed=quote.revisions[revision - 1].embed(ctx.me.colour))
            return

        def convert(revs: Sequence[QuoteRevision], page_id: int, total_pages: int):
            embed = discord.Embed(colour=ctx.me.colour, title=i18n("Quote #{}").format(int(quote)))
            embed.set_footer(text=i18n("Page {}/{}").format(page_id + 1, total_pages))

            for rev in revs:
                embed.add_field(name=rev.title, value=rev.summary(ctx.prefix), inline=False)

            return embed

        async with PaginateMenu(ctx, pages=chunks(quote.revisions, 5), converter=convert, actions={}):
            pass

    @quote.command(name="list")
    async def quote_list(self, ctx: RedContext, per_page: int = 8):
        """List the quotes in the current guild

        Maximum amount of quotes per page is 15; any higher values are silently reduced to this limit.
        """
        quotes = await Quote.all_quotes(ctx.guild)

        if not quotes:
            return await fmt(ctx, warning(i18n("This guild has no quotes! Use `{prefix}quote add` to add some!")))

        per_page = min(per_page, 15)

        # embeds allow up to 6k chars total, so let's take advantage of that
        max_len = 5000 // per_page
        # but ensure we don't go over the field value char limit
        if max_len > 1024:
            max_len = 1024

        def convert(pg: Sequence[Quote], page_id, total_pages):
            embed = discord.Embed(colour=ctx.me.colour, title=i18n("Guild Quotes"),
                                  description=i18n("Displaying {} out of {} quotes").format(len(pg), len(quotes)))
            embed.set_footer(text=i18n("Page {}/{}").format(page_id + 1, total_pages))
            for q in pg:
                embed.add_field(name=i18n("Quote #{}").format(q.id), value=trim_to(q.text, max_len), inline=False)
            return embed

        async with PaginateMenu(ctx, pages=chunks(quotes, per_page), converter=convert, actions={}):
            pass

    @quote.command(name="attribute", aliases=["author"])
    async def quote_attribute(self, ctx: RedContext, quote: int, *, author: discord.Member):
        """Attribute a quote to the specified user

        This requires you to be the quote creator, an administrator or moderator
        """
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(i18n("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(i18n("You aren't authorized to modify that quote")))
            return

        quote.edited = True
        quote.message_author = author
        await quote.save()
        await ctx.send(tick(i18n("Attributed quote #{} to **{}**.").format(int(quote), str(author))))

    @quote.command(name="remove", aliases=["rm", "delete"])
    async def quote_remove(self, ctx: RedContext, quote: int):
        """Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator,
        moderator, or the attributed message author.
        """
        quote = await Quote.get(ctx.guild, quote)
        if not quote:
            await ctx.send(warning(i18n("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(i18n("You aren't authorized to remove that quote")))
            return

        if await ConfirmMenu(ctx, content=self.DELETE_WARNING).prompt():
            await quote.delete()
            await ctx.send(tick(i18n("Quote successfully deleted.")))
        else:
            await ctx.send(i18n("Ok then."))
