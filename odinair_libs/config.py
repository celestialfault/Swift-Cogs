"""
Config helper utilities
"""

from typing import Sequence, Any, Dict

from redbot.core.config import Value, Group

__all__ = ["toggle", "group_toggle"]


async def toggle(value: Value) -> bool:
    """Toggle a config bool"""
    current = await value()
    await value.set(not current)
    return not current


async def group_toggle(group: Group, toggle_keys: Sequence[str], defaults: Dict[str, Any] = None):
    if defaults is None:
        defaults = group.defaults
    async with group() as settings:
        for key in defaults:  # copy defaults to the group data
            if key not in settings:
                settings[key] = defaults[key]
        for key in toggle_keys:  # toggle values that we want to toggle
            settings[key] = not settings[key]
        return settings  # return the changed settings
