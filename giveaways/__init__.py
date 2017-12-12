from redbot.core import Config
from redbot.core.bot import Red
from .giveaway import Giveaway
from .classes.base import setup as setup_base


def setup(bot: Red):
    config = Config.get_conf(Giveaway, identifier=45790424331, force_registration=True)
    config.register_guild(enabled=False, mod_only=True, pin_messages=False, giveaways=[])
    setup_base(bot, config)
    bot.add_cog(Giveaway(bot, config))
