import discord

from redbot.core import Config
from redbot.core.bot import Red

guild_cache = {}


class StarboardBase:
    config: Config = None
    bot: Red = None

    @staticmethod
    def get_starboard(guild: discord.Guild):
        from .guildstarboard import GuildStarboard
        if guild.id not in guild_cache:
            guild_cache[guild.id] = GuildStarboard(guild)
        return guild_cache[guild.id]

    @staticmethod
    def get_starboard_cache():
        return guild_cache

    def stats(self, member: discord.Member):
        from starboard.classes.starboarduser import StarboardUser
        # TODO: Cache these in some way?
        return StarboardUser(self.get_starboard(member.guild), member)
