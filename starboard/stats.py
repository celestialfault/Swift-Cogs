from typing import Iterable, Sequence, Dict, Optional

import discord

from starboard.i18n import i18n
from starboard.starboardguild import StarboardGuild
from starboard.base import get_starboard

from cog_shared.odinair_libs import format_int

__all__ = ("user_stats", "leaderboard_position", "leaderboard")


def _get_starrers(x: dict) -> Sequence[int]:
    return x.get("starrers", x.get("members", []))


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
        [x for x in messages if member.id in _get_starrers(x) and _is_author(x, member) is False]
    )

    received = sum(
        [
            len([y for y in _get_starrers(x) if y != member.id])
            for x in messages
            if _is_author(x, member) is True
        ]
    )

    messages = len(
        [
            x
            for x in messages
            if _is_author(x, member) is True and x.get("starboard_message", None) is not None
        ]
    )

    return {"given": given, "received": received, "messages": messages}


async def leaderboard(
    guild: discord.Guild, *, top: int = None
) -> Dict[str, Dict[discord.Member, int]]:
    starboard = get_starboard(guild)  # type: StarboardGuild
    message_data = (await starboard.messages()).values()

    def sort(i: Iterable, sort_index: int = 1):
        return {x: y for x, y in reversed(sorted(i, key=lambda x: x[sort_index])) if y}

    given = {}  # type: Dict[discord.Member, int]
    received = {}  # type: Dict[discord.Member, int]
    messages = {}  # type: Dict[discord.Member, int]

    for member in guild.members:
        data = await user_stats(member, messages=message_data)
        given[member] = data["given"]
        received[member] = data["received"]
        messages[member] = data["messages"]

    given, received, messages = (
        sort(given.items()), sort(received.items()), sort(messages.items())
    )

    if top:
        # noinspection PyTypeChecker
        given, received, messages = (
            dict(list(given.items())[:top]),
            dict(list(received.items())[:top]),
            dict(list(messages.items())[:top]),
        )

    return {"given": given, "received": received, "messages": messages}


async def leaderboard_position(member: discord.Member) -> Dict[str, str]:
    lb_data = await leaderboard(member.guild)
    return {
        k: "#{}".format(format_int(list(v.keys()).index(member) + 1))
        if member in v
        else i18n("unranked")
        for k, v in lb_data.items()
    }
