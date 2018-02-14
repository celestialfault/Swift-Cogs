from typing import Sequence, Dict, Optional, Tuple

from redbot.core.config import Value, Group

__all__ = ["toggle", "group_toggle"]


def parse_bool(val: str) -> Optional[bool]:
    if val in ("yes", "y", "on", "true"):
        return True
    elif val in ("no", "n", "off", "false"):
        return False
    return None


def parse_setting_param(param: str) -> Tuple[str, Optional[bool]]:
    param = param.split("=")
    if len(param) == 1:
        return param[0], None
    return param[0], parse_bool(param[1])


async def toggle(value: Value) -> bool:
    """Toggle a config bool

    Parameters
    ----------
    value: Value
        A Config ``Value`` object that is expected to return a bool-like value

    Returns
    --------
    bool
        The new value
    """
    current = not await value()
    await value.set(current)
    return current


async def group_toggle(group: Group, toggle_keys: Sequence[str], *, defaults: Dict[str, bool] = None,
                       slots: Sequence[str] = None) -> Dict[str, bool]:
    """Group config toggle

    Parameters
    -----------
    group: Group
        The Config ``Group`` to edit
    toggle_keys: Sequence[str]
        The keys in the ``Group`` to edit. These can be formatted similarly to `value=true` or `value=no` to specify
        a specific bool value
    defaults: Dict[str, bool]
        The ``Group`` defaults. Defaults to `group.defaults`
    slots: Sequence[str]
        The available keys in the ``Group`` to allow modification of

    Returns
    --------
    Dict[str, bool]
        The modified ``Group`` settings

    Raises
    -------
    RuntimeError
        If the given ``Group`` does not return a dict value
    """
    if defaults is None:
        defaults = group.defaults
    if slots is None:
        slots = toggle_keys
    toggle_keys = [x for x in toggle_keys if x.split("=")[0] in slots or x in slots]
    toggles = {}
    for item in toggle_keys:
        item = parse_setting_param(item)
        toggles[item[0]] = item[1]
    async with group() as settings:
        if not isinstance(settings, dict):
            raise RuntimeError("Group does not return a dict value")
        for key in defaults:
            val = defaults.get(key, False)
            if key not in settings:
                settings[key] = val
        for key in toggles:
            val = toggles.get(key, None)
            if val is None:
                val = not settings.get(key, False)
            settings[key] = val
        return settings
