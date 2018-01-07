import discord
from discord.ext import commands

from redbot.core import Config, RedContext
from redbot.core.bot import Red

from typing import Optional
from datetime import datetime


class Quote:
    """This is almost definitely a gross misuse of classes."""

    def __init__(self, bot: Red, **kwargs):
        self.guild = bot.get_guild(kwargs["guild_id"])
        self.author = self.guild.get_member(kwargs["author_id"])
        self.message_author = self.guild.get_member(kwargs["message_author_id"])
        self.text = kwargs["text"]
        self.id = kwargs["id"]
        self.timestamp = datetime.fromtimestamp(kwargs.get("timestamp", 0))


class Quotes:
    """Save and retrieve quotes"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=441356724, force_registration=True)
        self.data.register_guild(quotes=[])

    async def get_quote(self, guild: discord.Guild, quote: int) -> Optional[Quote]:
        """Gets a quote from the specified guild

        :param guild: The guild to get the quote from
        :param quote: The quote ID
        :return Optional[Quote]: Quote if the quote requested is found in the specified guild, None otherwise
        """
        quotes = list(await self.data.guild(guild).quotes())
        if len(quotes) >= quote and len(quotes) != 0:
            return Quote(self.bot, **quotes[quote - 1], id=quote)
        return None

    async def add_quote(self, text: str, author: discord.Member, message_author: discord.Member) -> Quote:
        """Adds a quote to a guild

        :param text: The text to quote
        :param author: The quote author
        :param message_author: The author of the quoted text, can be the same as author
        :return Quote: The created Quote object
        """
        guild = author.guild
        quote = {'author_id': author.id, 'text': text, 'message_author_id': message_author.id, 'guild_id': guild.id,
                 'timestamp': datetime.utcnow().timestamp()}
        async with self.data.guild(guild).quotes() as quotes:
            quotes.append(quote)
        return Quote(self.bot, **quote, id=len(quotes))

    async def remove_quote(self, quote: Quote) -> None:
        """Removes a quote

        :param quote: A Quote obtained from get_quote or add_quote
        :return None
        """
        quotes = list(await self.data.guild(quote.guild).quotes())
        del quotes[quote.id - 1]
        await self.data.guild(quote.guild).quotes.set(quotes)

    @commands.group(name="quote", aliases=["quotes"], invoke_without_command=True)
    async def _quote(self, ctx: RedContext, *quotes: int):
        """
        Save and retrieve quotes

        You can retrieve up to 3 quotes at once
        """
        if len(quotes) == 0 or len(quotes) > 3:
            await ctx.send_help()
            return
        retrieved = []
        for quote_id in quotes:
            if quote_id in retrieved:  # Don't send the same quote multiple times
                continue
            quote = await self.get_quote(ctx.guild, quote_id)
            if quote is None:
                await ctx.send("❌ Quote #{} doesn't exist".format(quote_id))
                continue
            embed = embed_quote(quote)
            await ctx.send(embed=embed)
            retrieved.append(quote_id)

    @_quote.command(name="add")
    async def _quote_add(self, ctx: RedContext, *, message: str):
        """Add a quote"""
        quote = await self.add_quote(message, ctx.author, ctx.author)
        await ctx.send("✅ Quote added", embed=embed_quote(quote))

    @_quote.command(name="message")
    async def _quote_message(self, ctx: RedContext, message: int):
        """Quote a message by it's ID

        The message specified must be in the same channel this command is executed in"""
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            await ctx.send("❌ I couldn't find that message")
        except discord.Forbidden:
            await ctx.send("❌ I'm not allowed to retrieve that message")
        else:
            quote = await self.add_quote(message.content, ctx.author, message.author)
            await ctx.send("✅ Quote added", embed=embed_quote(quote))

    @_quote.command(name="attribute", aliases=["author"])
    async def _quote_attribute(self, ctx: RedContext, quote: int, *, author: discord.Member):
        """
        Attribute a quote to the specified user

        This requires you to be the quote creator, an administrator or moderator
        """
        _quote = await self.get_quote(ctx.guild, quote)
        if _quote is None:
            await ctx.send("❌ That quote doesn't exist")
            return
        if not _quote.author or _quote.author.id != ctx.author.id:
            if await self.bot.is_owner(ctx.author):
                pass
            elif await self.bot.is_mod(ctx.author):
                pass
            else:
                return await ctx.send("❌ You aren't allowed to modify that quote")
        quotes = list(await self.data.guild(ctx.guild).quotes())
        quotes[quote - 1]["message_author_id"] = author.id
        await self.data.guild(ctx.guild).quotes.set(quotes)
        await ctx.send("✅ Attributed quote #{} to **{}**.".format(quote, str(author)))

    @_quote.command(name="remove", aliases=["rm", "delete"])
    async def _quote_remove(self, ctx: RedContext, quote: int):
        """
        Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator, moderator, or the quoted message author
        """
        quote = await self.get_quote(ctx.guild, quote)
        if not quote:
            return await ctx.send("❌ That quote doesn't exist")
        if not quote.author or quote.author.id != ctx.author.id:
            if quote.message_author and quote.message_author.id == ctx.author.id:
                pass
            elif await self.bot.is_owner(ctx.author):
                pass
            elif await self.bot.is_mod(ctx.author):
                pass
            else:
                return ctx.send("❌ You aren't allowed to remove that quote")
        await self.remove_quote(quote)
        await ctx.send("✅ Quote removed.")


def embed_quote(quote: Quote) -> discord.Embed:
    """
    Returns a built Embed object for the given Quote
    :param quote: A quote returned from get_quote or add_quote
    :return Embed: Created Embed of the given quote
    """
    colour = discord.Colour.blurple() if not quote.message_author else quote.message_author.colour
    embed = discord.Embed(colour=colour, description=quote.text, timestamp=quote.timestamp)

    if quote.message_author:  # Check if we found the message author
        embed.set_author(name=quote.message_author.display_name, icon_url=quote.message_author.avatar_url)
    else:
        if quote.author:  # Attempt to fall back to the quote creator
            embed.set_author(name=quote.author.display_name, icon_url=quote.author.avatar_url)
        else:
            embed.set_author(name="Unknown quote author", icon_url=quote.guild.icon_url)

    footer_str = "Quote #{0.id}"
    if quote.author and quote.message_author and quote.message_author.id != quote.author.id:
        footer_str = "Quote #{0.id} | Quoted by {0.author!s}"
    embed.set_footer(text=footer_str.format(quote))

    return embed
