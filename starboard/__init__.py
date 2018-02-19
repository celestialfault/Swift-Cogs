from redbot.core import Config
from redbot.core.bot import Red

from starboard.classes.starboardbase import StarboardBase


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        spec = await bot.cog_mgr.find_cog('odinair_libs')
        await bot.load_extension(spec)
    from .starboard import Starboard
    from .classes.starboardbase import setup as setup_base
    config = Config.get_conf(Starboard, identifier=45351212589, force_registration=True)
    config.register_guild(**{
        "messages": [],
        "blocks": [],
        "ignored_channels": [],
        "channel": None,
        "min_stars": 1,
        "respect_requirerole": True
    })
    setup_base(bot, config)
    bot.add_cog(Starboard(bot, config))
