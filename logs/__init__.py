from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .logs import Logs
    from odinair_libs.config import fix_config_fuckup
    c = Logs(bot)
    await fix_config_fuckup(c.config, identifier=35908345472, bot=bot)
    bot.add_cog(c)
