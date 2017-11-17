import discord
from discord.ext import commands

from redbot.core import Config
from redbot.core.bot import Red

from typing import Union
from .quote import Quote
from datetime import datetime


class Quotes:
    """Save and retrieve quotes"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=441356724, force_registration=True)
        default_guild = {"quotes": []}
        self.config.register_guild(**default_guild)

    async def get_quote(self, quote: int, guild: discord.Guild) -> Union[Quote, None]:
        """
        Gets a quote from the specified server
        :param quote: The quote ID
        :param guild: The guild to get the quote from
        :return Union[Quote, None]: Quote if the quote is found in the specified guild, None otherwise
        """
        quotes = await to_list(await self.config.guild(guild).quotes())
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
        quotes = await to_list(await self.config.guild(guild).quotes())
        quote = {
            "author_id": author.id,
            "text": text,
            "message_author_id": message_author.id,
            "guild_id": guild.id,
            "timestamp": datetime.utcnow().timestamp()
        }
        quotes.append(quote)
        await self.config.guild(guild).quotes.set(quotes)
        return Quote(self.bot, **quote, id=len(quotes))

    async def remove_quote(self, quote: Quote) -> None:
        """
        Removes a quote
        :param quote: A Quote obtained from get_quote or add_quote
        :return None
        """
        quotes = await to_list(await self.config.guild(quote.guild).quotes())
        del quotes[quote.id - 1]
        await self.config.guild(quote.guild).quotes.set(quotes)

    @commands.group(name="quote", aliases=["quotes"])
    async def quotecmd(self, ctx: commands.Context):
        """
        Quote management
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @quotecmd.command(name="get", aliases=["retrieve"])
    async def quotecmd_get(self, ctx: commands.Context, quote: int):
        """
        Retrieve a specified quote
        """
        quote = await self.get_quote(quote, ctx.guild)
        if not quote:
            return await ctx.send(":x: That quote doesn't exist")
        embed = await embed_quote(quote)
        await ctx.send(embed=embed)

    @quotecmd.command(name="add")
    async def quotecmd_add(self, ctx: commands.Context, message: str):
        """
        Add a quote
        """
        quote = await self.add_quote(message, ctx.author, ctx.author)
        await ctx.send(embed=await embed_quote(quote))

    @quotecmd.command(name="message")
    async def quotecmd_message(self, ctx: commands.Context, message: int):
        """
        Quote a message by it's ID
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            return await ctx.send(":x: I couldn't find that message")
        except discord.Forbidden:
            return await ctx.send(":x: I'm not allowed to retrieve that message")
        if message.guild.id != ctx.guild.id:
            return await ctx.send(":x: You can't quote messages not in the same guild")
        quote = await self.add_quote(message.content, ctx.author, message.author)
        await ctx.send(embed=await embed_quote(quote))

    @quotecmd.command(name="remove", aliases=["rm", "delete"])
    async def quotecmd_remove(self, ctx: commands.Context, quote: int):
        """
        Remove a quote by it's ID

        This requires you to either be the quote's creator, an administrator, moderator, or the quoted message author
        """
        quote = await self.get_quote(quote, ctx.guild)
        if not quote:
            return await ctx.send(":x: I couldn't find that quote")
        if quote.author.id != ctx.author.id:
            if quote.message_author.id == ctx.author.id:
                pass
            elif await self.bot.is_owner(ctx.author):
                pass
            elif await self.bot.is_mod(ctx.author):
                pass
            else:
                return ctx.send(":x: You aren't allowed to remove that quote")
        await self.remove_quote(quote)
        await ctx.send("✅ Quote removed.")


async def to_list(data) -> list:
    """
    This is an inherently terrible idea, and only exists because of Red's Config
    :param data: The data to turn into a list
    :return list: A created list object
    """
    __new = []
    for v in data:
        __new.append(v)
    return __new


async def embed_quote(quote: Quote) -> discord.Embed:
    """
    Returns an Embed of the given quote
    :param quote: A quote returned from get_quote or add_quote
    :return Embed: Created Embed of the given quote
    """
    embed = discord.Embed(colour=discord.Colour.blurple(), description=quote.text, timestamp=quote.timestamp)
    embed.set_author(name=quote.message_author.display_name, icon_url=quote.message_author.avatar_url)
    embed.set_footer(text="Quote #{} | Quoted by {}".format(quote.id, str(quote.author)))
    return embed
