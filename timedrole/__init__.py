from redbot.core.bot import Red


async def setup_libs(bot: Red):
    """Now featuring: A terrible misuse of Red's cog manager"""
    spec = await bot.cog_mgr.find_cog('odinair_libs')
    bot.load_extension(spec)
    from .timedrole import TimedRole
    bot.add_cog(TimedRole(bot))


def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        bot.loop.create_task(setup_libs(bot))
    else:
        from .timedrole import TimedRole
        bot.add_cog(TimedRole(bot))
