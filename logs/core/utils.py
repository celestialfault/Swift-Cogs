import collections
from typing import List, Dict, Any

from logs.core.i18n import _

__all__ = ('add_descriptions',)


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = f"**{item}** \N{EM DASH} {descriptions.get(item, _('No description set'))}"
    return "\n".join(items)


def replace_dict_items(dct: dict, replace_with: Any):
    new = []
    for key, item in dct.items():
        if isinstance(item, collections.MutableMapping):
            new.append((key, replace_dict_items(dict(item), replace_with)))
        else:
            new.append((key, replace_with))
    return dict(new)
