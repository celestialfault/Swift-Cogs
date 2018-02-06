from datetime import timedelta
from typing import Iterable, Tuple, Any, Dict, Union


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

    return (", " if not short_format else "").join(strings) if as_string is True else strings


def difference(list1: Iterable, list2: Iterable, *, check_val: bool = False, dict_values: bool = False)\
        -> Tuple[Union[Iterable, Dict], Union[Iterable, Dict]]:
    """Returns a tuple of lists based on the Iterable items passed in

    If check_val is True, this assumes the lists contain tuple-like items, and checks for True-ish items
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


def changed(before: Dict[Any, Any], after: Dict[Any, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    """Returns a list of added, removed, and changed items from two dict-like objects

    This assumes that the first key of an object is a unique key, and the second key is an item that can be changed
    """
    added, removed = difference(before, after, dict_values=True)
    changed_before = {x: before[x] for x in after if x in after and after[x] != before[x]}
    changed_after = {x: after[x] for x in after if x in before and before[x] != after[x]}
    return added, changed_before, changed_after, removed


def normalize(text, *, title_case: bool = True, **kwargs):
    text = str(text)
    text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text
