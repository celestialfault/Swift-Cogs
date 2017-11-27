import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.config import Value
from redbot.core.bot import Red

from typing import Optional
from .quote import Quote
from datetime import datetime


class Quotes:
    """Save and retrieve quotes"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=441356724, force_registration=True)
        default_guild = {"quotes": []}
        self.data.register_guild(**default_guild)

    async def get_quote(self, guild: discord.Guild, quote: int) -> Optional[Quote]:
        """
        Gets a quote from the specified server
        :param guild: The guild to get the quote from
        :param quote: The quote ID
        :return Optional[Quote]: Quote if the quote is found in the specified guild, None otherwise
        """
        quotes = await to_list(await self.data.guild(guild).quotes())
        if len(quotes) >= quote and len(quotes) != 0:
            return Quote(self.bot, **quotes[quote - 1], id=quote)
        return None

    async def add_quote(self, text: str, author: discord.Member, message_author: discord.Member) -> Quote:
        """
        Adds a quote to a server
        :param text: The text to quote
        :param author: The quote author
        :param message_author: The author of the quoted text, can be the same as author
        :return Quote: The created Quote object
        """
        guild = author.guild
        quotes = await to_list(await self.data.guild(guild).quotes())
        quote = {'author_id': author.id, 'text': text, 'message_author_id': message_author.id, 'guild_id': guild.id,
                 'timestamp': datetime.utcnow().timestamp()}
        quotes.append(quote)
        await self.data.guild(guild).quotes.set(quotes)
        return Quote(self.bot, **quote, id=len(quotes))

    async def remove_quote(self, quote: Quote) -> None:
        """
        Removes a quote
        :param quote: A Quote obtained from get_quote or add_quote
        :return None
        """
        quotes = await to_list(await self.data.guild(quote.guild).quotes())
        del quotes[quote.id - 1]
        await self.data.guild(quote.guild).quotes.set(quotes)

    @commands.group(name="quote", aliases=["quotes"])
    async def _quote(self, ctx: commands.Context):
        """
        Quote management
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_quote.command(name="get", aliases=["retrieve"])
    async def _quote_get(self, ctx: commands.Context, quote: int):
        """
        Retrieve a specified quote
        """
        quote = await self.get_quote(ctx.guild, quote)
        if not quote:
            return await ctx.send("❌ That quote doesn't exist")
        embed = await embed_quote(quote)
        await ctx.send(embed=embed)

    @_quote.command(name="add")
    async def _quote_add(self, ctx: commands.Context, message: str):
        """
        Add a quote
        """
        quote = await self.add_quote(message, ctx.author, ctx.author)
        await ctx.send(embed=await embed_quote(quote))

    @_quote.command(name="message")
    async def _quote_message(self, ctx: commands.Context, message: int):
        """
        Quote a message by it's ID. The message must be in the same channel the command is executed in.
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            return await ctx.send("❌ I couldn't find that message")
        except discord.Forbidden:
            return await ctx.send("❌ I'm not allowed to retrieve that message")
        quote = await self.add_quote(message.content, ctx.author, message.author)
        await ctx.send(embed=await embed_quote(quote))

    @_quote.command(name="attribute", aliases=["author"])
    async def _quote_attribute(self, ctx: commands.Context, quote: int, *, author: discord.Member):
        """
        Attribute a quote to the specified user

        This requires you to be the quote creator, an administrator or moderator
        """
        _quote = await self.get_quote(ctx.guild, quote)
        if _quote.author.id != ctx.author.id:
            if await self.bot.is_owner(ctx.author):
                pass
            elif await self.bot.is_mod(ctx.author):
                pass
            else:
                return await ctx.send("❌ You aren't allowed to modify that quote")
        quotes = await to_list(await self.data.guild(ctx.guild).quotes())
        quotes[quote - 1]["message_author_id"] = author.id
        await self.data.guild(ctx.guild).quotes.set(quotes)
        await ctx.send("✅ Attributed quote #{} to **{}**.".format(quote, str(author)))

    @_quote.command(name="remove", aliases=["rm", "delete"])
    async def _quote_remove(self, ctx: commands.Context, quote: int):
        """
        Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator, moderator, or the quoted message author
        """
        quote = await self.get_quote(ctx.guild, quote)
        if not quote:
            return await ctx.send("❌ I couldn't find that quote")
        if quote.author.id != ctx.author.id:
            if quote.message_author.id == ctx.author.id:
                pass
            elif await self.bot.is_owner(ctx.author):
                pass
            elif await self.bot.is_mod(ctx.author):
                pass
            else:
                return ctx.send("❌ You aren't allowed to remove that quote")
        await self.remove_quote(quote)
        await ctx.send("✅ Quote removed.")


async def to_list(data: Value) -> list:
    """
    This is an __inherently terrible idea__, and only exists because of Red's Config.

    (what I'm saying that you probably shouldn't use this.)
    :param data: The data to turn into a list
    :return list: A created list object
    """
    __new = []
    # noinspection PyTypeChecker
    for v in data:
        __new.append(v)
    return __new


async def embed_quote(quote: Quote) -> discord.Embed:
    """
    Returns a created Embed object for the given Quote
    :param quote: A quote returned from get_quote or add_quote
    :return Embed: Created Embed of the given quote
    """
    colour = discord.Colour.blurple() if not quote.message_author else quote.message_author.colour
    embed = discord.Embed(colour=colour, description=quote.text, timestamp=quote.timestamp)

    if quote.message_author:  # Check if we found the message author
        embed.set_author(name=quote.message_author.display_name, icon_url=quote.message_author.avatar_url)
    else:
        embed.set_author(name="Quote author not found", icon_url=quote.guild.icon_url)

    if quote.author:  # Check if we found the quote creator
        # Check that the author is not the same person
        if quote.message_author and quote.message_author.id == quote.author.id:
            embed.set_footer(text="Quote #{}".format(quote.id))
        else:
            embed.set_footer(text="Quote #{} | Quoted by {}".format(quote.id, str(quote.author)))
    else:
        embed.set_footer(text="Quote #{}".format(quote.id))

    return embed
