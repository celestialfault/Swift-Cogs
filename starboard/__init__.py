from redbot.core import Config

from starboard.classes.starboardbase import StarboardBase


def build_config(cog, bot):
    from .classes.starboardbase import setup as setup_base
    config = Config.get_conf(cog, identifier=45351212589, force_registration=True)
    config.register_guild(**{
        "messages": [],
        "blocks": [],
        "ignored_channels": [],
        "channel": None,
        "min_stars": 1,
        "respect_requirerole": True
    })
    setup_base(bot, config)
    return config


async def setup_libs(bot):
    spec = await bot.cog_mgr.find_cog('odinair_libs')
    bot.load_extension(spec)
    from .starboard import Starboard
    bot.add_cog(Starboard(bot, build_config(Starboard, bot)))


def setup(bot):
    if 'OdinairLibs' not in bot.cogs:
        bot.loop.create_task(setup_libs(bot))
    else:
        from .starboard import Starboard
        bot.add_cog(Starboard(bot, build_config(Starboard, bot)))
