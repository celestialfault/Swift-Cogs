from redbot.core.bot import Red

bot = None  # type: Red
"""
The following cog acts mostly as a dummy cog for allowing other cogs to detect
if the shared libraries this package contains is loaded
"""


class OdinairLibs:
    """This cog only contains utilities for other cogs, and as such isn't useful on its own."""
    VERSION = (0, 3, 0)

    def __init__(self):
        from odinair_libs import converters, formatting, menus, checks, config
        self.converters = converters
        self.formatting = formatting
        self.menus = menus
        self.checks = checks
        self.config = config


def setup(bot_: Red):
    global bot  # type: Red
    bot = bot_
    bot.add_cog(OdinairLibs())
