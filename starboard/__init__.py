from redbot.core.bot import Red

from starboard.classes.base import StarboardBase


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .starboard import Starboard
    from odinair_libs.config import fix_config_fuckup
    cog = Starboard(bot)
    await fix_config_fuckup(cog.config, identifier=45351212589, bot=bot)
    bot.add_cog(cog)
