from asyncio import Queue
from typing import Iterable

import discord

from redbot.core.bot import Red

__all__ = ("cog_name", "IterQueue")


class IterQueue(Queue, Iterable):
    """Iterable version of an asyncio Queue"""
    def __iter__(self):
        while not self.empty():
            yield self.get_nowait()

    async def __aiter__(self):
        while True:
            yield await self.get()


def cog_name(bot: Red, name: str):
    """Returns a case-sensitive name from a case-insensitive cog name"""
    return discord.utils.find(lambda x: x.lower() == name.lower(), bot.cogs.keys())
