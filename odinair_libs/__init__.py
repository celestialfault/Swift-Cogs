from odinair_libs import converters, formatting, menus

"""
The following cog acts mostly as a dummy cog for allowing other cogs of mine to detect
if the shared libraries this package contains is loaded

If these aren't loaded, most cogs that need them will do a terrible workaround to load them.

("terrible workaround" is read as "abusing Red's Cog manager for ~~evil~~ good(?)")
"""


class OdinairLibs:
    """
    This cog isn't useful on it's own.

    This mostly serves as an identifier to check if the shared libraries this package contains is loaded and usable.
    """
    VERSION = (0, 1, 0)

    def __init__(self):
        self.converters = converters
        self.formatting = formatting
        self.menus = menus


def setup(bot):
    bot.add_cog(OdinairLibs())
