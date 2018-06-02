import asyncio

import discord
from redbot.core.bot import Red

from starboard.base import get_starboard, get_starboard_cache
from starboard.guild import StarboardGuild
from starboard.shared import log

import_lock = asyncio.Lock()
__all__ = ("import_data", "NoMotorError", "import_lock")


r"""
'alright wtf is this and why does this exist'

  My v2 starboard cog ( which can be found at https://github.com/notodinair/Red-Cogs ) used MongoDB
  instead of flat-file JSON storage.

  This resulted in the awkward situation of not being able to import config data / starred messages
  via Red's data converter, as it was designed to handle flat-file JSON storage, and not MongoDB.

'why did you use mongodb anyway'

  ¯\_(ツ)_/¯

  It was definitely a better decision than to store every message in a giant JSON file.

  I think.
  I'll get back to you on that.
"""


class NoMotorError(Exception):
    pass


async def import_data(bot: Red, mongo_uri: str):
    try:
        from motor import motor_asyncio as motor
    except ImportError:
        raise NoMotorError

    log.info("Starting v2 data migration...")
    db = motor.AsyncIOMotorClient(mongo_uri)
    for starboard in get_starboard_cache().values():
        await starboard.purge_cache(0, update_items=False)

    async with import_lock:
        async for item in db.starboard.stars.find({}):
            if not isinstance(item, dict):
                continue
            message_id = item.get("message_id")
            if message_id is None:
                continue
            channel_id = item.get("channel_id")
            channel: discord.TextChannel = bot.get_channel(int(channel_id))
            if channel is None:
                continue
            guild: discord.Guild = getattr(channel, "guild", None)
            if guild is None:
                continue
            starboard: StarboardGuild = get_starboard(guild)
            await starboard.messages.set_raw(
                str(message_id),
                value={
                    "channel_id": channel.id,
                    "author_id": None,
                    "starred_by": [item.get("starrers", [])],
                    "starboard_message": item.get("starboard_message", None),
                    "hidden": item.get("removed", False),
                },
            )

    log.info("v2 data migration complete.")
