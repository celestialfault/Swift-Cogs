from redbot.core import Config
from redbot.core.bot import Red

from .logs import Logs

defaults_guild = {
    "format": "EMBED",
    "ignored": False,
    "log_channels": {
        "roles": None,
        "guild": None,
        "messages": None,
        "members": None,
        "channels": None,
        "voice": None,
        "emoji": None
    },
    "roles": {
        "create": False,
        "delete": False,
        "name": False,
        "permissions": False,
        "hoist": False,
        "mention": False,
        "position": False,
        "colour": False
    },
    "guild": {
        "name": False,
        "2fa": False,
        "verification": False,
        "afk": False,
        "region": False,
        "content_filter": False,
        "owner": False
    },
    "messages": {
        "edit": False,
        "delete": False
    },
    "members": {
        "join": False,
        "leave": False,
        "name": False,
        "nickname": False,
        "roles": False
    },
    "channels": {
        "create": False,
        "delete": False,
        "name": False,
        "topic": False,
        "position": False,
        "category": False,
        "bitrate": False,
        "user_limit": False
    },
    "voice": {
        "channel": False,
        "selfmute": False,
        "servermute": False,
        "selfdeaf": False,
        "serverdeaf": False
    },
    "emojis": False
}


def setup(bot: Red):
    from .guildlog import setup as setup_formatter
    config = Config.get_conf(Logs, identifier=35908345472, force_registration=True)
    config.register_guild(**defaults_guild)
    config.register_channel(ignored=False)
    config.register_member(ignored=False)
    setup_formatter(bot, config)
    bot.add_cog(Logs(bot, config))
