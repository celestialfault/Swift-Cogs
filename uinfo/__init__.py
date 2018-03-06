from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .uinfo import UInfo
    bot.add_cog(UInfo(bot))
