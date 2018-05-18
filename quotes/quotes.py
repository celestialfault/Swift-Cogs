from pathlib import Path
from random import randint

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import cog_i18n
from redbot.core.utils.chat_formatting import error, warning

from cog_shared.swift_libs import (
    Page,
    PaginatedMenu,
    chunks,
    confirm,
    fmt,
    tick,
    to_lazy_translator,
    trim_to,
)
from quotes.editor import QuoteEditor
from quotes.quote import Quote, conf, ensure_can_modify, i18n
from quotes.v2_import import import_v2_data

lazyi18n = to_lazy_translator(i18n)


@cog_i18n(i18n)
class Quotes:
    """Save and retrieve quotes"""

    __author__ = "odinair <odinair@odinair.xyz>"

    DELETE_WARNING = lazyi18n(
        "Are you sure you want to delete this quote?\n\n"
        "Unless you have a time machine, this action **cannot be undone**."
    )

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = conf
        Quote.bot = self.bot

    @commands.group(name="quote", aliases=["quotes"], invoke_without_command=True)
    @commands.guild_only()
    async def quote(self, ctx: commands.Context, quote: Quote = None):
        """Save and retrieve quotes

        If no quote is given, a random quote is retrieved instead.
        """
        if quote is None:
            quotes = len(await self.config.guild(ctx.guild).quotes())
            if not quotes:
                await ctx.send_help()
                return
            quote = await Quote.get(ctx.guild, randint(1, quotes))

        await ctx.send(embed=quote.embed)

    @quote.command(hidden=True, name="lorem")
    @checks.is_owner()
    async def quote_lorem_ipsum(self, ctx: commands.Context, amount: int = 100):
        """Generates some junk lorem ipsum quotes.

        This is basically only useful if you're working on Quotes itself,
        and need some data to test with.

        **Requires the `loremipsum` module (`[p]pipinstall loremipsum`).**
        """
        try:
            import loremipsum
        except ImportError:
            await ctx.send(
                error(
                    i18n(
                        "Failed to import the `loremipsum` module; please do `{prefix}pipinstall "
                        "loremipsum` and use this command again."
                    ).format(
                        prefix=ctx.prefix
                    )
                )
            )
            return

        import re

        for _ in range(amount):
            await Quote.create(
                " ".join(
                    [
                        " ".join(
                            [re.sub(r"[Bb]\'(.*)\'", lambda x: x.group(1), x) for x in y.split()]
                        ).capitalize()
                        for y in loremipsum.get_sentences(3)
                    ]
                ),
                ctx.author,
            )

        await ctx.send("Generated {} quotes.".format(amount))

    @quote.command(hidden=True, name="clearall")
    @checks.guildowner()
    async def quote_clearall(self, ctx: commands.Context):
        if not await confirm(
            ctx,
            content=i18n(
                "Are you sure you want to reset all quotes?\n\nUnless you have a time machine, "
                "**this action is irreversible.**"
            ),
        ):
            await ctx.send(i18n("Operation cancelled."))
            return

        await self.config.guild(ctx.guild).quotes.set([])
        await ctx.tick()

    @quote.command(hidden=True, name="v2_import")
    @checks.is_owner()
    async def quote_v2_import(self, ctx: commands.Context, path: str):
        """Import quotes data from a Red v2 instance"""
        path = Path(path) / "data" / "quotes" / "quotes.json"
        if not path.is_file():
            await ctx.send(error(i18n("That file path doesn't seem to be valid")))
            return
        async with ctx.typing():
            await import_v2_data(config=self.config, path=path)
        await ctx.send(tick(i18n("Imported data successfully.")))

    @quote.command(name="add")
    async def quote_add(self, ctx: commands.Context, *, message: str):
        """Add a quote"""
        quote = await Quote.create(message, ctx.author, ctx.author)
        await ctx.send(tick(i18n("Quote added")), embed=quote.embed)

    @quote.command(name="message")
    async def quote_message(self, ctx: commands.Context, message: int):
        """Quote a message by it's ID

        The message specified must be in the same channel this command is executed in

        You can obtain a message's ID by enabling Developer Mode in your Appearance
        settings, and clicking Copy ID in the message's context menu
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            await ctx.send(
                warning(i18n("I couldn't find that message. (is it in a different channel?)"))
            )
        except discord.Forbidden:
            await ctx.send(warning(i18n("I'm not allowed to retrieve that message")))
        else:
            quote = await Quote.create(message.content, ctx.author, message.author)
            await ctx.send(tick(i18n("Quote added")), embed=quote.embed)

    @quote.group(name="edit", aliases=["modify"], invoke_without_command=True)
    async def quote_edit(self, ctx: commands.Context, quote: Quote):
        """Interactive quote editor

        This requires you to be the quote creator, the attributed author
        or a guild moderator or administrator.
        """
        await ensure_can_modify(ctx.author, quote)
        await QuoteEditor(ctx, quote)()

    @quote_edit.command(name="author")
    async def edit_author(self, ctx: commands.Context, quote: Quote, *, author: discord.Member):
        """Attribute a quote to the specified user

        This requires you to be the quote creator, an administrator or moderator
        """
        await ensure_can_modify(ctx.author, quote)

        quote.edited = True
        quote.message_author = author
        await quote.save()
        await ctx.send(
            tick(i18n("Attributed quote #{} to **{}**.").format(int(quote), str(author)))
        )

    @quote.command(name="list")
    async def quote_list(self, ctx: commands.Context, per_page: int = 8):
        """List the quotes in the current guild

        Maximum amount of quotes per page is 15; any higher values are silently reduced
        to this limit.
        """
        quotes = await Quote.all_quotes(ctx.guild)

        if not quotes:
            return await fmt(
                ctx, warning(i18n("This guild has no quotes! Use `{prefix}quote add` to add some!"))
            )

        per_page = min(per_page, 15)

        def convert(page: Page):
            embed = discord.Embed(
                colour=ctx.me.colour,
                title=i18n("Guild Quotes"),
                description=i18n("Displaying {} out of {} quotes").format(
                    len(page.data), len(quotes)
                ),
            )
            embed.set_footer(text=i18n("Page {0.current} out of {0.total}").format(page))
            for q in page.data:
                embed.add_field(
                    name=i18n("Quote #{}").format(q.id),
                    value=trim_to(q.text, min(5000 // per_page, 1024)),
                    inline=False,
                )
            return embed

        await PaginatedMenu(
            ctx=ctx,
            pages=list(chunks(quotes, per_page)),
            converter=convert,
            actions={},
            wrap_around=True,
        )

    @quote.command(name="remove", aliases=["rm", "delete"])
    async def quote_remove(self, ctx: commands.Context, quote: Quote):
        """Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator,
        moderator, or the attributed message author.
        """
        await ensure_can_modify(ctx.author, quote)

        if await confirm(ctx, content=warning(self.DELETE_WARNING)):
            await quote.delete()
            await ctx.send(tick(i18n("Quote successfully deleted.")))
        else:
            await ctx.send(i18n("Ok then."))
