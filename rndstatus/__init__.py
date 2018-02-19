from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        spec = await bot.cog_mgr.find_cog('odinair_libs')
        await bot.load_extension(spec)
    from .rndstatus import RNDStatus
    bot.add_cog(RNDStatus(bot))
