import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import warning

from cog_shared.odinair_libs.formatting import tick
from cog_shared.odinair_libs.menus import ReactMenu, confirm, PostMenuAction, prompt

from quotes.quote import Quote, conf, _


class Quotes:
    """Save and retrieve quotes"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        Quote.bot = bot
        self.config = conf

    @commands.group(name="quote", aliases=["quotes"], invoke_without_command=True)
    async def quote(self, ctx: RedContext, quote: int):
        """Save and retrieve quotes"""
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(_("That quote doesn't exist")))
            return
        await ctx.send(embed=quote.embed)

    @quote.command(name="add")
    async def _quote_add(self, ctx: RedContext, *, message: str):
        """Add a quote"""
        quote = await Quote.create(message, ctx.author, ctx.author)
        await ctx.send(tick(_("Quote added")), embed=quote.embed)

    @quote.command(name="message")
    async def _quote_message(self, ctx: RedContext, message: int):
        """Quote a message by it's ID

        The message specified must be in the same channel this command is executed in

        You can obtain a message's ID by enabling Developer Mode in your Appearance settings,
        and clicking Copy ID in the message's context menu
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            await ctx.send(warning(_("I couldn't find that message. (is it in a different channel?)")))
        except discord.Forbidden:
            await ctx.send(warning(_("I'm not allowed to retrieve that message")))
        else:
            quote = await Quote.create(message.content, ctx.author, message.author)
            await ctx.send(tick(_("Quote added")), embed=quote.embed)

    @quote.command(name="edit", aliases=["modify"])
    async def _quote_edit(self, ctx: RedContext, quote: int):
        """Interactive quote editor

        This requires you to be the quote creator, the attributed author
        or a guild moderator or administrator.
        """
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(_("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(_("You aren't authorized to modify that quote")))
            return

        embed = discord.Embed(title=_("Edit Quote"),
                              description=_("What action(s) would you like to take?\n\n"
                                            "\N{BUST IN SILHOUETTE} \N{EM DASH} Attribute quote\n"
                                            "\N{MEMO} \N{EM DASH} Edit content\n"
                                            "\N{WASTEBASKET} \N{EM DASH} Delete quote\n"
                                            "\N{CROSS MARK} \N{EM DASH} Cancel"))

        actions = {
            "attribute": "\N{BUST IN SILHOUETTE}",
            "edit_content": "\N{MEMO}",
            "delete": "\N{WASTEBASKET}",
            "cancel": "\N{CROSS MARK}"
        }

        menu = ReactMenu(ctx=ctx, actions=actions, embed=embed, post_action=PostMenuAction.DELETE)
        while True:
            async with menu as result:
                if result.timed_out or result == "cancel":
                    break

                elif result == "attribute":
                    msg = await prompt(ctx, content=_("Who would you like to attribute this quote to?"), timeout=30.0,
                                       delete_messages=True)
                    if not msg:
                        continue

                    try:
                        member = await commands.MemberConverter().convert(ctx, msg.content)
                    except commands.BadArgument:
                        await ctx.send(warning(_("Failed to convert `{}` into a Member - try again?")
                                               .format(msg.content)),
                                       delete_after=30.0)
                        continue
                    else:
                        quote.edited = True
                        quote.message_author = member
                        await quote.save()
                        await ctx.send(tick(_("Attributed quote to **{}**.").format(str(member))), delete_after=30.0)

                elif result == "edit_content":
                    msg = await prompt(ctx, content=_("Please enter the new content for the quote"), timeout=120.0,
                                       delete_messages=True)
                    if not msg:
                        continue

                    quote.edited = True
                    quote.text = msg.content
                    await quote.save()
                    await ctx.send(tick(_("Modified quote contents successfully.")), delete_after=30.0)

                elif result == "delete":
                    if await confirm(ctx, message=_("Are you sure you want to delete this quote?\n\n"
                                                    "**This action cannot be undone!**"),
                                     colour=discord.Colour.red()):
                        await quote.delete()
                        await ctx.send(tick(_("Quote successfully deleted.")), delete_after=30.0)
                        break

        try:
            await result.message.delete()
        except (discord.HTTPException, AttributeError):
            pass

    @quote.command(name="attribute", aliases=["author"])
    async def _quote_attribute(self, ctx: RedContext, quote: int, *, author: discord.Member):
        """Attribute a quote to the specified user

        This requires you to be the quote creator, an administrator or moderator
        """
        quote = await Quote.get(ctx.guild, quote)
        if quote is None:
            await ctx.send(warning(_("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(_("You aren't authorized to modify that quote")))
            return

        quote.edited = True
        quote.message_author = author
        await quote.save()
        await ctx.send(tick(_("Attributed quote #{} to **{}**.").format(quote, str(author))))

    @quote.command(name="remove", aliases=["rm", "delete"])
    async def _quote_remove(self, ctx: RedContext, quote: int):
        """Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator, moderator, or the quoted message author
        """
        quote = await Quote.get(ctx.guild, quote)
        if not quote:
            await ctx.send(warning(_("That quote doesn't exist")))
            return
        if not await quote.can_modify(ctx.author):
            await ctx.send(warning(_("You aren't authorized to remove that quote")))
            return

        if await confirm(ctx, message=_("Are you sure you want to delete this quote?\n\n"
                                        "**This action cannot be undone!**"),
                         colour=discord.Colour.red()):
            await quote.delete()
            await ctx.send(tick(_("Quote successfully deleted.")))
        else:
            await ctx.send(_("Ok then."))
