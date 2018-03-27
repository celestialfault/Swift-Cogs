import discord

try:
    from motor import motor_asyncio as motor
except ImportError:
    motor = False

from redbot.core.bot import Red

from starboard.base import get_starboard, get_starboard_cache
from starboard.starboardguild import StarboardGuild


async def v2_import(bot: Red, mongo_uri: str):
    if motor is False:
        raise RuntimeError("motor was not found; cannot continue")
    db = motor.AsyncIOMotorClient(mongo_uri)
    async for item in db.starboard.stars.find({}):
        if not isinstance(item, dict):
            continue
        message_id = item.get("message_id", None)
        if message_id is None:
            continue
        channel_id = item.get("channel_id", None)
        channel: discord.TextChannel = bot.get_channel(int(channel_id))
        if channel is None:
            continue
        guild: discord.Guild = getattr(channel, "guild", None)
        if guild is None:
            continue
        starboard: StarboardGuild = await get_starboard(guild)
        await starboard.messages.set_raw(str(message_id), value={
            "channel_id": channel.id,
            "author_id": None,
            "members": [item.get("starrers", [])],
            "starboard_message": item.get("starboard_message", None),
            "hidden": item.get("removed", False)
        })
    for starboard in get_starboard_cache():
        await starboard.purge_cache(0)
