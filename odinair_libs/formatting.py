from datetime import timedelta
from typing import Iterable, Tuple


def td_format(td_object: timedelta, short_format: bool = False, as_string: bool = True) -> str:
    # this function is originally from StackOverflow with modifications made
    # https://stackoverflow.com/a/13756038
    seconds = int(td_object.total_seconds())
    if seconds < 0:  # Remove negative signs from numbers
        seconds = int(str(seconds)[1:])
    elif seconds == 0:  # Properly handle timedelta objects with no time
        s = "0 seconds" if not short_format else "0s"
        return s if as_string else [s]
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

    return ", ".join(strings) if as_string is True else strings


def difference(list1: Iterable, list2: Iterable, *, check_val: bool = False) -> Tuple[list, list]:
    """Returns a tuple of lists based on the Iterable items passed in

    If check_val is True, this assumes the lists are tuple-like, and checks for True-ish items"""
    if check_val:
        # Only include items that evaluate to True
        list1 = filter(None, list1)
        list2 = filter(None, list2)

    added = [x for x in list2 if x not in list1]
    removed = [x for x in list1 if x not in list2]
    return added, removed


def normalize(text, *, title_case: bool = True, **kwargs):
    text = str(text)
    text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text
