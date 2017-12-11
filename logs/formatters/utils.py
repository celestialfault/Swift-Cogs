import discord

from datetime import timedelta
from typing import Iterable, Optional, Union


# ~~stolen~~ borrowed from StackOverflow
# https://stackoverflow.com/a/13756038
def td_format(td_object: timedelta) -> str:
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)


def difference(list1: Iterable, list2: Iterable, *, check_val: bool, formatter=None, formatter_params=None) -> dict:
    if not formatter:
        # noinspection PyUnusedLocal
        def noop_format(_input, **kwargs):
            return _input
        formatter = noop_format
    if not formatter_params:
        formatter_params = {}
    removed = [formatter(x, **formatter_params) for x in list1 if x not in list2]
    added = [formatter(x, **formatter_params) for x in list2 if x not in list1]
    if check_val:
        removed = [formatter(x) for x, val in list1 if val and not getattr(list1, x)]
        added = [formatter(x) for x, val in list2 if val and not getattr(list1, x)]
    return dict(added=added, removed=removed)


def normalize(text: str, *, title_case: bool=True, **kwargs):
    text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text


def find_check(**kwargs) -> Optional[Union[discord.Member, discord.TextChannel, discord.Guild]]:
    if kwargs.get('after', None):
        return extract_check(kwargs.get('after', None))
    elif kwargs.get('member', None):
        return extract_check(kwargs.get('member', None))
    elif kwargs.get('guild', None):
        return extract_check(kwargs.get('guild', None))
    elif kwargs.get('channel', None):
        return extract_check(kwargs.get('channel', None))
    else:
        return None


def extract_check(obj) -> Optional[Union[discord.Member, discord.TextChannel, discord.Guild]]:
    if isinstance(obj, discord.Member):
        return obj
    elif isinstance(obj, discord.Message):
        return obj.author
    elif isinstance(obj, discord.Guild):
        return obj
    elif isinstance(obj, discord.TextChannel):
        return obj
    else:
        return None
