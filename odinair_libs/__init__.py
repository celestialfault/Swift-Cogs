"""
The following cog acts mostly as a dummy cog for allowing other cogs to detect
if the shared libraries this package contains is loaded, and in addition to allowing other cogs
to load the shared libraries without using imports
"""


class OdinairLibs:
    """This cog only contains utilities for other cogs, and as such isn't useful on its own."""
    VERSION = (0, 5, 0)

    def __init__(self):
        from odinair_libs import converters, formatting, menus, checks, config
        self.converters = converters
        self.formatting = formatting
        self.menus = menus
        self.checks = checks
        self.config = config


def setup(bot):
    bot.add_cog(OdinairLibs())
