from redbot.core.bot import Red


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        spec = await bot.cog_mgr.find_cog('odinair_libs')
        await bot.load_extension(spec)
    from .punish import Punish
    bot.add_cog(Punish(bot))
