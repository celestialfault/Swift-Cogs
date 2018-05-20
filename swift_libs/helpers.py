"""Various miscellaneous helper functions & classes"""

from asyncio import Queue
from typing import Iterable, Optional

import discord
from redbot.core.bot import Red
from redbot.core import commands

__all__ = ("IterableQueue", "ExtendedQueue", "prompt", "confirm")


class ExtendedQueue(Queue):
    """A version of an asyncio Queue with helpful features"""

    def remove(self, item):
        if not hasattr(self, "_queue"):
            raise KeyError
        del self._queue[self._queue.index(item)]

    def __delitem__(self, key: int):
        if not hasattr(self, "_queue"):
            raise KeyError
        del self._queue[key]

    def __contains__(self, item):
        if not hasattr(self, "_queue"):
            return False
        return item in self._queue


class IterableQueue(ExtendedQueue, Iterable):
    """Iterable version of an asyncio Queue. Extends `ExtendedQueue`"""

    def __iter__(self):
        while not self.empty():
            yield self.get_nowait()


async def confirm(ctx, default: bool = False, **kwargs):
    from .menus import Menu, PostAction

    return (
        await Menu(
            ctx=ctx,
            actions={True: "\N{WHITE HEAVY CHECK MARK}", False: "\N{CROSS MARK}"},
            default=default,
            **kwargs,
        ).prompt(post_action=PostAction.DELETE_MESSAGE)
    ).item


async def prompt(
    ctx: commands.Context,
    *,
    content: str = None,
    embed: discord.Embed = None,
    delete_messages: bool = False,
    timeout: float = 30.0,
) -> Optional[discord.Message]:
    """Prompt a user for input

    Parameters
    -----------
    ctx: Context
        The Red context object
    content: str
        The message content to send. If `embed` is given, this is optional
    embed: discord.Embed
        The embed to send. If `content` is given, this is optional
    delete_messages: bool
        Whether or not the sent messages are deleted when this function returns
    timeout: float
        How long to wait for a response from the user

    Returns
    --------
    Optional[discord.Message]
    """
    bot: Red = ctx.bot
    message_sent = await ctx.send(content=content, embed=embed)
    message_recv = None

    try:
        message_recv = await bot.wait_for(
            "message",
            timeout=timeout,
            check=lambda x: x.author == ctx.author and x.channel == ctx.channel,
        )
    except TimeoutError:
        pass
    finally:
        if (
            delete_messages
            and ctx.guild
            and ctx.channel.permissions_for(ctx.guild.me).manage_messages
        ):
            if message_recv is not None:
                try:
                    await ctx.channel.delete_messages([message_sent, message_recv])
                except discord.HTTPException:
                    pass
            else:
                await message_sent.delete()

    return message_recv
