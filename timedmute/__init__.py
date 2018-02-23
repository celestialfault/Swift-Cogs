from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        spec = await bot.cog_mgr.find_cog('odinair_libs')
        await bot.load_extension(spec)
    from .timedmute import TimedMute
    bot.add_cog(TimedMute(bot))
