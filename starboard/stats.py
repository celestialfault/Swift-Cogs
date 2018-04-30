from typing import Iterable, Sequence, Dict

import discord

from starboard.i18n import i18n
from starboard.starboardguild import StarboardGuild
from starboard.base import get_starboard

from cog_shared.odinair_libs import format_int

__all__ = ('user_stats', 'leaderboard_position', 'leaderboard')


def _get_starrers(x: dict) -> Sequence[int]:
    return x.get('starrers', x.get('members', []))


async def user_stats(member: discord.Member, *, messages: Iterable = None) -> Dict[str, int]:
    starboard = get_starboard(member.guild)
    if messages is None:
        messages = (await starboard.messages()).values()

    messages = list(filter(lambda x: x.get("hidden", False) is False, messages))

    given = len([x for x in messages if member.id in _get_starrers(x) and member.id != x.get('author_id', None)])
    received = sum([len([y for y in x.get('starrers', x.get('members', [])) if y != member.id])
                    for x in messages if x.get("author_id", None) == member.id])
    messages = len([x for x in messages
                    if x.get("author_id", None) == member.id and x.get("starboard_message", None) is not None])

    return {
        "given": given,
        "received": received,
        "messages": messages
    }


async def leaderboard(guild: discord.Guild, *, top: int = None) -> Dict[str, Dict[discord.Member, int]]:
    starboard = get_starboard(guild)  # type: StarboardGuild
    message_data = (await starboard.messages()).values()

    given = {}  # type: Dict[discord.Member, int]
    received = {}  # type: Dict[discord.Member, int]
    messages = {}  # type: Dict[discord.Member, int]

    for member in guild.members:
        data = await user_stats(member, messages=message_data)
        given[member] = data['given']
        received[member] = data['received']
        messages[member] = data['messages']

    given = {x: y for x, y in reversed(sorted(given.items(), key=lambda x: x[1])) if y}
    received = {x: y for x, y in reversed(sorted(received.items(), key=lambda x: x[1])) if y}
    messages = {x: y for x, y in reversed(sorted(messages.items(), key=lambda x: x[1])) if y}

    if top:
        # noinspection PyTypeChecker
        given = dict(list(given.items())[:top])
        # noinspection PyTypeChecker
        received = dict(list(received.items())[:top])
        # noinspection PyTypeChecker
        messages = dict(list(messages.items())[:top])

    return {"given": given, "received": received, "messages": messages}


async def leaderboard_position(member: discord.Member) -> Dict[str, str]:
    lb_data = await leaderboard(member.guild)
    return {k: "#{}".format(format_int(list(v.keys()).index(member) + 1)) if member in v else i18n("unranked")
            for k, v in lb_data.items()}
