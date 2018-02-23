from redbot.core import Config
from redbot.core.bot import Red

from starboard.classes.starboardbase import StarboardBase


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .starboard import Starboard
    from .classes.starboardbase import setup as setup_base
    from odinair_libs.config import fix_config_fuckup
    config = Config.get_conf(None, identifier=45351212589, force_registration=True, cog_name="Starboard")
    config.register_guild(**{
        "messages": [],
        "blocks": [],
        "ignored_channels": [],
        "channel": None,
        "min_stars": 1,
        "respect_requirerole": True
    })
    await fix_config_fuckup(config, identifier=45351212589, bot=bot)
    setup_base(bot, config)
    bot.add_cog(Starboard(bot, config))
