from typing import List, Dict

from logs.core.i18n import _

__all__ = ('add_descriptions',)


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = f"**{item}** \N{EM DASH} {descriptions.get(item, _('No description set'))}"
    return "\n".join(items)
