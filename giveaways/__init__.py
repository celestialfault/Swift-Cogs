from redbot.core import Config
from redbot.core.bot import Red

from .giveaways import Giveaways


def setup(bot: Red):
    from .base import setup as setup_base
    config = Config.get_conf(Giveaways, identifier=45790424331, force_registration=True)
    config.register_guild(mod_only=True, pin_messages=False, giveaways=[])
    setup_base(bot, config)
    bot.add_cog(Giveaways(bot, config))
