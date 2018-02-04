from redbot.core import Config
from redbot.core.bot import Red

from .starboard import Starboard

from .classes.exceptions import *
from .classes.starboardbase import StarboardBase


def setup(bot: Red):
    from .classes.starboardbase import setup as setup_base
    config = Config.get_conf(Starboard, identifier=45351212589, force_registration=True)
    config.register_guild(**{
        "messages": [],
        "blocks": [],
        "ignored_channels": [],
        "channel": None,
        "min_stars": 1,
        "respect_requirerole": False
    })
    setup_base(bot, config)
    bot.add_cog(Starboard(bot, config))
