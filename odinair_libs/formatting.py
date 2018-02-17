from datetime import timedelta
from typing import Iterable, Tuple, Any, Dict, Union

import discord

import odinair_libs as libs

import textwrap
import inspect

__all__ = ["td_format", "difference", "changed", "normalize", "attempt_emoji", "get_source", "tick"]


def tick(text: str):
    return "\N{WHITE HEAVY CHECK MARK} {}".format(text)


def get_source(fn):
    """Get the source code for a function

    Parameters
    ----------
    fn
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
    lines, _ = inspect.getsourcelines(fn.__code__)
    return textwrap.dedent("".join(lines))


def attempt_emoji(fallback: str, *, emoji_id: int = None, emoji_name: str = None,
                  guild: discord.Guild = None, **kwargs):
    """Attempt to get an emoji from all guilds the bot is in or from a specific guild

    Parameters
    -----------
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
    emojis = libs.bot.emojis if guild is None else guild.emojis
    emoji = None
    if emoji_id is not None:
        emoji = discord.utils.get(emojis, id=emoji_id, **kwargs)
    if emoji is None and emoji_name is not None:
        emoji = discord.utils.get(emojis, name=emoji_name, **kwargs)
    if emoji is None and kwargs:
        emoji = discord.utils.get(emojis, **kwargs)
    return emoji or fallback


def td_format(td_object: timedelta, short_format: bool = False, as_string: bool = True,
              milliseconds: bool = False) -> str:
    """Format a timedelta into a human readable output

    Parameters
    -----------
    td_object: timedelta
        A timedelta object to format
    short_format: bool
        Returns in short format, such as '10d2h' instead of '10 days 2 hours'
    as_string: bool
        If this is False, all the strings are returned in a list instead of a joined string
    milliseconds: bool
        If this is True, milliseconds are also appended
    """
    # this function is originally from StackOverflow with modifications made
    # https://stackoverflow.com/a/13756038
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365), ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24), ('hour', 60 * 60), ('minute', 60), ('second', 1)]
    if short_format is True:
        periods = [
            ('y', 60 * 60 * 24 * 365), ('mo', 60 * 60 * 24 * 30),
            ('d', 60 * 60 * 24), ('h', 60 * 60), ('m', 60), ('s', 1)]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if short_format:
                strings.append("%s%s" % (period_value, period_name))
            elif period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    if milliseconds is True and (td_object.microseconds / 1000) > 0:
        ms = td_object.microseconds / 1000
        strings.append("%s%s%s%s" % (ms, " " if not short_format else "", "ms" if short_format else "millisecond",
                                     "s" if ms != 1 and not short_format else ""))

    return (", " if not short_format else "").join(strings) if as_string is True else strings


def difference(list1: Iterable, list2: Iterable, *, check_val: bool = False, dict_values: bool = False)\
        -> Tuple[Union[Iterable, Dict], Union[Iterable, Dict]]:
    """Returns a tuple of added or removed items based on the Iterable items passed in

    If check_val is True, this assumes the lists contain tuple-like items, and checks for True-ish items

    Parameters
    -----------
    list1: Iterable
        The first list to check
    list2: Iterable
        The second list to check
    check_val: bool
        Whether or not to check values. If this is True, this assumes the lists contain tuple-like or are dicts
    dict_values: bool
        If this is True, this returns a dict of both item keys and values instead of lists of added and removed keys

    Returns
    --------
    dict
        Returned if ``dict_values`` is True
    list
        Returned if ``dict_values`` is False
    """
    if check_val:
        # Only include items that evaluate to True
        list1 = [x for x, val in list1 if val]
        list2 = [x for x, val in list2 if val]

    added = [x for x in list2 if x not in list1]
    removed = [x for x in list1 if x not in list2]

    if dict_values:
        added = {x: list2[x] for x in added}
        removed = {x: list1[x] for x in removed}
    return added, removed


def changed(before: Dict[Any, Any], after: Dict[Any, Any]) \
        -> Tuple[Dict[Any, Any], Dict[Any, Tuple[Any, Any]], Dict[Any, Any]]:
    """Returns a list of added, removed, and changed items from two dict-like objects

    This assumes that the first key of an object is a unique key, and the second key is an item that can be changed

    Parameters
    -----------
    before: Dict[Any, Any]
        The list before any possible changes
    after: Dict[Any, Any]
        The list after any possible changes

    Returns
    --------
    Tuple[Dict[Any, Any], Dict[Any, Tuple[Any, Any]], Dict[Any, Any]]
        Returns a tuple of dicts in the following order:

        - Added items
        - Changed items with tuples of before and after values
        - Removed items
    """
    added, removed = difference(before, after, dict_values=True)
    return added, {x: (before[x], after[x]) for x in after if x in before and before[x] != after[x]}, removed


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
