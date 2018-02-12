async def setup_libs(bot):
    spec = await bot.cog_mgr.find_cog('odinair_libs')
    bot.load_extension(spec)
    from .userprofiles import UserProfile
    bot.add_cog(UserProfile(bot))


def setup(bot):
    if 'OdinairLibs' not in bot.cogs:
        bot.loop.create_task(setup_libs(bot))
    else:
        from .userprofiles import UserProfile
        bot.add_cog(UserProfile(bot))
