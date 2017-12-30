import discord

from redbot.core import Config
from redbot.core.bot import Red


class StarboardBase:
    @staticmethod
    def starboard(guild: discord.Guild):
        from .guildstarboard import GuildStarboard
        if guild.id not in guild_cache:
            guild_cache[guild.id] = GuildStarboard(guild, config, bot)
        return guild_cache[guild.id]

    @staticmethod
    def guild_starboard_cache():
        return guild_cache

    async def message(self, message: discord.Message, auto_create: bool=False):
        if not message.guild:
            raise ValueError("Message must be in a Guild")
        return await self.starboard(message.guild).message(message, auto_create=auto_create)


def setup(_bot: Red, _config: Config):
    global bot
    bot = _bot
    global config
    config = _config
    global guild_cache
    guild_cache = {}
