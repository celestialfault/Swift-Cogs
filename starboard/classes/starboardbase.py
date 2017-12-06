import discord
from redbot.core import Config
from redbot.core.bot import Red


class StarboardBase:
    def __init__(self):
        self._guild_cache = {}

    def starboard(self, guild: discord.Guild):
        from .guildstarboard import GuildStarboard
        if guild.id not in self._guild_cache:
            self._guild_cache[guild.id] = GuildStarboard(guild, config, bot)
        return self._guild_cache[guild.id]

    def message(self, message: discord.Message, *, auto_create: bool=False):
        if not message.guild:
            raise ValueError("Message must be in a Guild")
        return self.starboard(message.guild).message(message, auto_create=auto_create)


def setup(_bot: Red, _config: Config):
    global bot
    bot = _bot
    global config
    config = _config
