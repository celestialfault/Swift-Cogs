import discord

from redbot.core import Config
from redbot.core.bot import Red

__all__ = ("get_starboard", "get_starboard_cache", "StarboardBase")

_guild_cache = {}
bot: Red = None
config: Config = None


def get_starboard(guild: discord.Guild):
    from starboard.guild import StarboardGuild

    if guild.id not in _guild_cache:
        sb = StarboardGuild(guild)
        _guild_cache[guild.id] = sb
    return _guild_cache[guild.id]


def get_starboard_cache():
    return _guild_cache


class StarboardBase:

    @property
    def config(self):
        return config

    @config.setter
    def config(self, cfg: Config):
        global config
        config = cfg

    @property
    def bot(self):
        return bot

    @bot.setter
    def bot(self, red: Red):
        global bot
        bot = red
