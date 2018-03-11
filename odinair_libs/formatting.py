import re
from datetime import timedelta

from redbot.core import RedContext
from types import FunctionType
from typing import Iterable, Tuple, Dict, Union

import discord
from redbot.core.bot import Red

from textwrap import dedent
from inspect import getsourcelines

__all__ = ["td_format", "difference", "normalize", "attempt_emoji", "get_source", "tick", "chunks", "cmd_help"]


def tick(text: str):
    return f"\N{WHITE HEAVY CHECK MARK} {text}"


def get_source(fn: FunctionType) -> str:
    """Get the source code for a function

    Parameters
    ----------
    fn: FunctionType
        The function to get the source for

    Returns
    --------
    str
        The source code for ``fn``

    Raises
    -------
    OSError
        If the source code cannot be retrieved, such as if the function is defined in a repl
    """
    lines, firstln = getsourcelines(fn.__code__)
    lines = dedent("".join(lines))
    return lines


def attempt_emoji(bot: Red, fallback: str, *, emoji_id: int = None, emoji_name: str = None,
                  guild: discord.Guild = None, **kwargs):
    """Attempt to get an emoji from all guilds the bot is in or from a specific guild

    Parameters
    -----------
    bot: Red
        The Red bot instance
    fallback: str
        A fallback string to return if neither emoji_id nor emoji_id resolves
    emoji_id: int
        The emoji ID to attempt to resolve
    emoji_name: str
        An emoji name to attempt to resolve. This is ignored if ``emoji_id`` resolves
    guild: discord.Guild
        A guild to search instead of attempting all emojis the bot has access to
    **kwargs
        Any additional keyword arguments that can be used to find a specific emoji

        An example would be `animated=False` to only find static emojis

    Returns
    --------
    discord.Emoji
        A resolved Emoji
    str
        The fallback string if neither ``emoji_id`` nor ``emoji_name`` resolve
    """
    if not any([emoji_id, emoji_name, kwargs]):
        return fallback
    emojis = bot.emojis if guild is None else guild.emojis
    emoji = None
    if emoji_id is not None:
        emoji = discord.utils.get(emojis, id=emoji_id, **kwargs)
    if emoji is None and emoji_name is not None:
        emoji = discord.utils.get(emojis, name=emoji_name, **kwargs)
    if emoji is None and kwargs:
        emoji = discord.utils.get(emojis, **kwargs)
    return emoji or fallback


_time_periods = {
    "long": {
        "year": 60 * 60 * 24 * 365,
        "month": 60 * 60 * 24 * 30,
        "day": 60 * 60 * 24,
        "hour": 60 * 60,
        "minute": 60,
        "second": 1
    },
    "short": {
        "y": 60 * 60 * 24 * 365,
        "mo": 60 * 60 * 24 * 30,
        "d": 60 * 60 * 24,
        "h": 60 * 60,
        "m": 60,
        "s": 1
    }
}


def td_format(td_object: timedelta, short_format: bool = False, milliseconds: bool = False,
              append_str: bool = False) -> str:
    """Format a timedelta into a human readable output

    Parameters
    -----------
    td_object: timedelta
        A timedelta object to format
    short_format: bool
        Returns in short format, such as '10d2h' instead of '10 days 2 hours'
    milliseconds: bool
        If this is True, milliseconds are also appended.

        Note: Milliseconds are rounded to the nearest full number, and as such this may not be fully accurate
    append_str: bool
        Whether or not to append or prepend `in` or `ago` depending on if `td_object` is in the future or past
    """
    # this function is originally from StackOverflow with modifications made
    # https://stackoverflow.com/a/13756038
    seconds = int(td_object.total_seconds())
    iter_ = "long" if not short_format else "short"
    periods_ = [(x, _time_periods[iter_][x]) for x in _time_periods[iter_]]
    past = False

    if seconds < 0:
        past = True
        seconds = int(re.sub(r"^-+", "", str(seconds)))
    elif seconds == 0 and not milliseconds:
        return "0 seconds" if not short_format else "0s"

    strings = []
    for period_name, period_seconds in periods_:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural = "s" if period_value != 1 and short_format is False else ""
            strings.append("{value}{space}{name}{plural}".format(
                value=period_value, name=period_name, plural=plural, space=" " if not short_format else ""))

    if milliseconds is True and (td_object.microseconds / 1000) > 0:
        ms = round(td_object.microseconds / 1000)
        if ms:
            space = " " if not short_format else ""
            period_name = "ms" if short_format else "millisecond" + "s" if ms != 1 else ""
            strings.append(f"{ms!s}{space}{period_name}")

    built = (", " if not short_format else "").join(strings)
    if not append_str:
        return built
    fmt = "in {}" if not past else "{} ago"
    return fmt.format(built)


def difference(list1: Iterable, list2: Iterable, *, check_val: bool = False, return_dict: bool = False)\
        -> Tuple[Union[Iterable, Dict], Union[Iterable, Dict]]:
    """Returns a tuple of added or removed items based on the Iterable items passed in

    Parameters
    -----------
    list1: Iterable
        The first list to check
    list2: Iterable
        The second list to check
    check_val: bool
        Whether or not to check values. If this is True, this assumes the lists contain tuple-like or are dicts
    return_dict: bool
        If this is True, this returns a dict of both item keys and values instead of lists of added and removed keys

    Returns
    --------
    dict
        Returned if ``return_dict`` is True
    list
        Returned if ``return_dict`` is False
    """
    if check_val:
        # Only include items that evaluate to True
        list1 = [x for x, val in list1 if val]
        list2 = [x for x, val in list2 if val]

    added = [x for x in list2 if x not in list1]
    removed = [x for x in list1 if x not in list2]

    if return_dict:
        added = {x: list2[x] for x in added}
        removed = {x: list1[x] for x in removed}
    return added, removed


def normalize(text, *, title_case: bool = True, underscores: bool = True, **kwargs):
    """Attempts to normalize a string

    Parameters
    -----------
    text: Any
        The string or object to attempt to normalize. This is casted to str for you
    title_case: bool
        Returns the formatted string as a Title Case string. Any substitions specified as keyword arguments are done
        before the string is title cased.
    underscores: bool
        Whether or not underscores are replaced with spaces
    **kwargs: Dict[str, Any]
        A dict of raw string keys with substitution values
    """
    text = str(text)
    if underscores:
        text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text


def chunks(l, n):  # https://stackoverflow.com/a/312464
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough,
    # so this is mostly what I'd consider "good enough"
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
