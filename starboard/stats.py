from typing import Dict, Iterable, Optional, Sequence

import discord

from starboard.base import get_starboard
from starboard.guild import StarboardGuild
from starboard.i18n import i18n

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

    received_data = [
        len([y for y in _get_starrers(x) if y != member.id])
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
    starboard = get_starboard(guild)  # type: StarboardGuild
    message_data = (await starboard.messages()).values()

    def sort(i: Iterable, sort_index: int = 1):
        return {x: y for x, y in reversed(sorted(i, key=lambda x: x[sort_index])) if y}

    given = {}  # type: Dict[discord.Member, int]
    received = {}  # type: Dict[discord.Member, int]
    messages = {}  # type: Dict[discord.Member, int]
    max_received = {}  # type: Dict[discord.Member, int]

    for member in guild.members:
        data = await user_stats(member, messages=message_data)
        given[member] = data["given"]
        received[member] = data["received"]
        messages[member] = data["messages"]
        max_received[member] = data["max_received"]

    given, received, messages, max_received = (
        sort(given.items()),
        sort(received.items()),
        sort(messages.items()),
        sort(max_received.items()),
    )

    if top:
        # noinspection PyTypeChecker
        given, received, messages, max_received = (
            dict(list(given.items())[:top]),
            dict(list(received.items())[:top]),
            dict(list(messages.items())[:top]),
            dict(list(max_received.items())[:top]),
        )

    return {
        "given": given,
        "received": received,
        "messages": messages,
        "max_received": max_received,
    }


async def leaderboard_position(member: discord.Member) -> Dict[str, str]:
    lb_data = await leaderboard(member.guild)
    return {
        k: "#{}".format("{:,}".format(list(v.keys()).index(member) + 1))
        if member in v
        else i18n("unranked")
        for k, v in lb_data.items()
    }
