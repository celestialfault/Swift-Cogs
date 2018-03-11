"""
Shared library for all my cogs.

The below cog (OdinairLibs) acts mostly as a dummy cog for allowing other cogs to detect
if the shared libraries this package contains is loaded, and in addition to allowing other cogs
to load the shared libraries without using imports
"""
from odinair_libs import converters, formatting, menus, checks, config


class OdinairLibs:
    """This cog only contains utilities for other cogs, and as such isn't useful on its own."""
    VERSION = (0, 7, 0)

    def __init__(self):
        self.converters = converters
        self.formatting = formatting
        self.menus = menus
        self.checks = checks
        self.config = config


__author__ = "odinair"
__version__ = ".".join([str(x) for x in OdinairLibs.VERSION])


def setup(bot):
    bot.add_cog(OdinairLibs())
