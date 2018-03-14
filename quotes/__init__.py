async def setup(bot):
    if 'OdinairLibs' not in bot.cogs:
        await bot.load_extension(await bot.cog_mgr.find_cog('odinair_libs'))
    from .quotes import Quotes
    bot.add_cog(Quotes(bot))
