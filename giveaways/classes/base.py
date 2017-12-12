import discord

from redbot.core.bot import Red
from redbot.core import Config

from .giveaway import GuildGiveaway

_cache = {}


def setup(_bot: Red, _config: Config):
    global config
    config = _config
    global bot
    bot = _bot


class GiveawayBase:
    @staticmethod
    def guild_config(guild: discord.Guild):
        return config.guild(guild)

    @staticmethod
    async def create_entry(message=discord.Message, creator=discord.Member, description: str=None):
        async with GiveawayBase.guild_config(message.guild).giveaways() as giveaways:
            if discord.utils.find(lambda entry: entry["message_id"] == message.id, giveaways):
                raise RuntimeError("Cannot create entry for a message that already exists")
            giveaways.append({
                "creator": creator.id,
                "message_id": message.id,
                "channel_id": message.channel.id,
                "winner": None,
                "ended": False,
                "entrants": [],
                "description": description or "No description provided"
            })
            if message.id in _cache:
                del _cache[message.id]

    @staticmethod
    async def giveaway_message(message: discord.Message, *, creator: discord.Member = None, auto_create: bool = False,
                               description: str=None):
        if message.id in _cache:
            return _cache[message.id]
        data = list(await GiveawayBase.guild_config(message.guild).giveaways())
        entry = discord.utils.find(lambda _entry: _entry["message_id"] == message.id, data)
        if entry or auto_create:
            entry = entry if entry else {"creator": None}
            creator = creator if not entry["creator"] else discord.utils.find(
                lambda member: member.id == entry["creator"],
                message.guild.members)
            giveaway = GuildGiveaway(message, creator, config)
            await giveaway.setup(auto_create=auto_create, description=description)
            _cache[message.id] = giveaway
            return giveaway
        else:
            _cache[message.id] = None
            return None

    @staticmethod
    async def get_giveaways(guild: discord.Guild, channel: discord.TextChannel = None):
        def __filter(item):
            return not item["ended"] and item["channel_id"] == channel.id if channel else True

        return list(filter(__filter, await GiveawayBase.guild_config(guild).giveaways()))
