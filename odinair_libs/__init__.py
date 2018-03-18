"""
Shared library for all my cogs.

The below cog (OdinairLibs) acts mostly as a dummy cog for allowing other cogs to detect
if the shared libraries this package contains is loaded, and in addition to allowing other cogs
to load the shared libraries without using imports
"""
from redbot.core.bot import Red

from odinair_libs import converters, formatting, menus, checks, config

__all__ = ['setup', 'converters', 'formatting', 'menus', 'checks', 'config']


class OdinairLibs:
    """This cog mostly contains utilities for other cogs, and as such isn't very useful on its own."""
    VERSION = (0, 7, 2)
    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = ".".join([str(x) for x in VERSION])

    def __init__(self, bot: Red):
        self.bot = bot
        self.converters = converters
        self.formatting = formatting
        self.menus = menus
        self.checks = checks
        self.config = config


def setup(bot: Red):
    bot.add_cog(OdinairLibs(bot))
