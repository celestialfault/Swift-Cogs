from typing import Dict, Iterable, Optional

import discord

from starboard.base import get_starboard
from starboard.guild import StarboardGuild
from starboard.message import resolve_starred_by

__all__ = ("user_stats", "leaderboard")


def _is_author(x: dict, member: discord.Member) -> Optional[bool]:
    author = x.get("author_id", None)
    if author is None:
        return None
    return member.id == x.get("author_id", None)


async def user_stats(member: discord.Member, *, messages: Iterable = None) -> Dict[str, int]:
    starboard = get_starboard(member.guild)
    if messages is None:
        messages = (await starboard.messages()).values()

    messages = list(filter(lambda x: x.get("hidden", False) is False, messages))

    given = len(
        [
            x
            for x in messages
            if member.id in resolve_starred_by(x) and _is_author(x, member) is False
        ]
    )

    received_data = [
        len([y for y in resolve_starred_by(x) if y != member.id])
        for x in messages
        if _is_author(x, member) is True
    ]

    received_max = max(received_data) if received_data else 0
    received = sum(received_data)

    messages = len(
        [
            x
            for x in messages
            if _is_author(x, member) is True and x.get("starboard_message", None) is not None
        ]
    )

    return {
        "given": given,
        "received": received,
        "messages": messages,
        "max_received": received_max,
    }


async def leaderboard(
    guild: discord.Guild, *, top: int = None
) -> Dict[str, Dict[discord.Member, int]]:
    starboard: StarboardGuild = get_starboard(guild)
    message_data = (await starboard.messages()).values()

    def sort(d: dict, sort_index: int = 1):
        return {x: y for x, y in reversed(sorted(d.items(), key=lambda x: x[sort_index])) if y}

    data: Dict[str, Dict[discord.Member, int]] = {}
    for member in guild.members:
        if member.bot:
            continue
        mdata = await user_stats(member, messages=message_data)
        for indx, val in mdata.items():
            if indx not in data:
                data[indx] = {}
            data[indx][member] = val

    return {
        x: sort(y) if top is None else dict(list(sort(y).items())[:top]) for x, y in data.items()
    }
