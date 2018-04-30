import collections
from typing import List, Dict

from logs.core.i18n import i18n

__all__ = ('add_descriptions', 'replace_dict_items')


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = "**{}** \N{EM DASH} {}".format(
            item,
            descriptions.get(item, i18n('No description set'))
        )
    return "\n".join(items)


def replace_dict_items(dct: dict, replace_with):
    new = []
    for key, item in dct.items():
        if isinstance(item, collections.MutableMapping):
            new.append((key, replace_dict_items(dict(item), replace_with)))
        else:
            new.append((key, replace_with))
    return dict(new)
