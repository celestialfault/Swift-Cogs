from copy import deepcopy
from typing import Dict, Any

from redbot.core import Config

from logs.core.log import log

root_defaults = {
    "ignore": {"channels": [], "members": [], "roles": [], "member_roles": [], "guild": False}
}

config = Config.get_conf(None, cog_name="Logs", identifier=2401248235421)


def rebuild_defaults() -> None:
    from logs.modules import modules

    defaults = {}  # type: Dict[str, Dict[str, Any]]

    for mod in modules.values():
        mod = mod(guild=None)

        if mod.config_scope not in defaults:
            defaults[mod.config_scope] = deepcopy(root_defaults)

        mod_defaults = {**mod.defaults, "_log_channel": None}
        defaults[mod.config_scope][mod.name] = mod_defaults

    for scope, values in defaults.items():
        log.debug("setting scope {} defaults w/ {} item(s)".format(scope, len(values.keys())))
        config.register_custom(scope, **values)
