import inspect
import collections

from datetime import timedelta

from typing import Iterable, Tuple, Dict, Union

import discord
import re

from redbot.core.bot import Red
from redbot.core import RedContext

from textwrap import dedent

from odinair_libs.converters import td_seconds

__all__ = ("td_format", "difference", "normalize", "attempt_emoji", "get_source",
           "tick", "chunks", "cmd_help", "flatten", "fmt")


async def fmt(ctx: RedContext, text: str, *args, **kwargs) -> None:
    await ctx.send(text.format(*args, **kwargs, prefix=ctx.prefix))


def flatten(d, parent_key='', sep='_'):  # https://stackoverflow.com/a/6027615
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def tick(text: str):
    return f"\N{WHITE HEAVY CHECK MARK} {text}"


def get_source(fn) -> str:
    """Get the source code for an object

    This function effectively acts an alias for the following:

    >>> from textwrap import dedent
    >>> from inspect import getsource
    >>> source = dedent(getsource(fn))

    Parameters
    -----------
    fn: FunctionType
        The function to get the source for

    Returns
    --------
    str
        The source code for ``fn``
    """
    return dedent(inspect.getsource(fn))


def attempt_emoji(bot: Red, fallback: str, guild: discord.Guild = None, **kwargs):
    """Attempt to get an emoji from all guilds the bot is in or from a specific guild

    Parameters
    -----------
    bot: Red
        The Red bot instance
    fallback: str
        A fallback string to return if neither emoji_id nor emoji_id resolves
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
    if not kwargs.keys():
        raise TypeError('expected at least one keyword argument, received none')
    return discord.utils.get(bot.emojis if guild is None else guild.emojis, **kwargs) or fallback


time_periods = [
    (td_seconds(days=365), "year"),
    (td_seconds(days=30), "month"),
    (td_seconds(days=7), "week"),
    (td_seconds(days=1), "day"),
    (td_seconds(hours=1), "hour"),
    (td_seconds(minutes=1), "minute"),
    (td_seconds(seconds=1), "second")
]


def td_format(td_object: timedelta, milliseconds: bool = False, append_str: bool = False) -> str:
    """Format a timedelta into a human readable output

    Parameters
    -----------
    td_object: timedelta
        A timedelta object to format
    milliseconds: bool
        If this is True, milliseconds are also appended.

        Note: Milliseconds are rounded to the nearest full number, and as such this may not be fully accurate
    append_str: bool
        Whether or not to append or prepend `in` or `ago` depending on if `td_object` is in the future or past
    """
    # this function is originally from StackOverflow
    # https://stackoverflow.com/a/13756038

    seconds = td_object.total_seconds()
    past = False
    if seconds < 0:
        past = True
        seconds = float(re.sub(r"^-+", "", str(seconds)))
    elif seconds == 0:
        return "0 seconds"

    strs = []

    for period_seconds, period_name in time_periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural = "s" if period_value != 1 else ""
            strs.append(" ".join([str(round(period_value)), f"{period_name}{plural}"]))

    if milliseconds is True:
        ms = round(td_object.microseconds / 1000)
        if ms > 0:
            plural = "s" if ms != 1 else ""
            strs.append(f"{ms} millisecond{plural}")

    built = ", ".join(strs)
    if not append_str:
        return built
    return ("in {}" if not past else "{} ago").format(built)


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


async def cmd_help(ctx: RedContext, cmd: str = "") -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough,
    # so this is mostly what I'd consider "good enough"
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
