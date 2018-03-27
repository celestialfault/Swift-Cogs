import discord

from redbot.core import Config
from redbot.core.bot import Red

__all__ = ("get_starboard", "get_starboard_cache", "get_stats", "StarboardBase", "setup")

_guild_cache = {}
bot: Red = None
config: Config = None


def setup(bot_: Red, config_: Config):
    global bot
    bot = bot_
    global config
    config = config_


async def get_starboard(guild: discord.Guild):
    from starboard.starboardguild import StarboardGuild
    if guild.id not in _guild_cache:
        sb = StarboardGuild(guild)
        _guild_cache[guild.id] = sb
        await sb.init()
    return _guild_cache[guild.id]


def get_starboard_cache():
    return _guild_cache


async def get_stats(member: discord.Member):
    from starboard.starboarduser import StarboardUser
    return StarboardUser(await get_starboard(member.guild), member)


class StarboardBase:
    @property
    def config(self):
        return config

    @property
    def bot(self):
        return bot
