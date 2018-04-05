import asyncio

import discord

from redbot.core.bot import Red

from starboard.base import get_starboard, get_starboard_cache
from starboard.starboardguild import StarboardGuild
from starboard.log import log

try:
    from motor import motor_asyncio as motor
except ImportError:
    motor = False

migrate_lock = asyncio.Lock()
__all__ = ('dump_caches', 'v2_import')


r"""
'emma wtf is this and why does this exist'

  My v2 starboard cog ( which can be found at https://github.com/notodinair/Red-Cogs ) used MongoDB
  instead of flat-file JSON storage.

  This resulted in the awkward situation of not being able to import config data / starred messages via
  Red's data converter, as it was designed to handle flat-file JSON storage, and not MongoDB.

'why tf did you use mongodb anyway?'

  ¯\_(ツ)_/¯
"""


class NoMotorException(Exception):
    pass


async def dump_caches():
    for starboard in get_starboard_cache().values():
        await starboard.purge_cache(0, update_items=False)


async def v2_import(bot: Red, mongo_uri: str):
    if motor is False:
        raise NoMotorException()
    log.info("Starting v2 data migration...")
    db = motor.AsyncIOMotorClient(mongo_uri)
    await dump_caches()
    log.info("Attempting to retrieve lock")
    async with migrate_lock:
        log.info("Lock retrieved, beginning...")
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
                "starrers": [item.get("starrers", [])],
                "starboard_message": item.get("starboard_message", None),
                "hidden": item.get("removed", False)
            })
    await dump_caches()
    log.info("v2 data migration complete.")
