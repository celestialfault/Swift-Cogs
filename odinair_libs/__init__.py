from odinair_libs import converters, formatting, menus, checks

"""
The following cog acts mostly as a dummy cog for allowing other cogs to detect
if the shared libraries this package contains is loaded
"""


class OdinairLibs:
    """This cog only contains utilities for other cogs, and as such isn't useful on its own."""
    VERSION = (0, 2, 0)

    def __init__(self):
        self.converters = converters
        self.formatting = formatting
        self.menus = menus
        self.checks = checks


def setup(bot):
    bot.add_cog(OdinairLibs())
