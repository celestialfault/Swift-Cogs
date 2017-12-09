from redbot.core import Config
from redbot.core.bot import Red
from .logs import Logs
from .formatters.base import setup as setup_formatter

defaults_guild = {
    "format": "TEXT",
    "log_channels": {
        "roles": None,
        "guild": None,
        "messages": None,
        "members": None,
        "channels": None,
        "voice": None
    },
    "roles": {
        "create": False,
        "delete": False,
        "update": {
            "name": False,
            "permissions": False,
            "hoist": False,
            "mention": False,
            "position": False
        }
    },
    "guild": {
        "name": False,
        "2fa": False,
        "verification": False,
        "afk": False,
        "owner": False
    },
    "messages": {
        "edit": False,
        "delete": False
    },
    "members": {
        "join": False,
        "leave": False,
        "update": {
            "name": False,
            "nickname": False,
            "roles": False
        }
    },
    "channels": {
        "create": False,
        "delete": False,
        "update": {
            "name": False,
            "topic": False,
            "position": False,
            "category": False
        }
    },
    "voice": {
        "join": False,
        "leave": False,
        "switch": False,
        "selfmute": False,
        "servermute": False,
        "selfdeaf": False,
        "serverdeaf": False
    }
}


def setup(bot: Red):
    config = Config.get_conf(Logs, identifier=35908345472, force_registration=True)
    config.register_guild(**defaults_guild)
    setup_formatter(bot, config)
    bot.add_cog(Logs(bot, config))
