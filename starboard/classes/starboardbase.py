import discord

from redbot.core import Config
from redbot.core.bot import Red

guild_cache = {}


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


def setup(bot_: Red, config_: Config):
    global bot
    bot = bot_
    global config
    config = config_
