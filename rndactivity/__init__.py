from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .rndactivity import RNDActivity
    bot.add_cog(RNDActivity(bot))
