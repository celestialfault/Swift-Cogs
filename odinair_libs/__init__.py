"""
Shared library for all my cogs
"""

from . import converters, formatting, menus, checks  # noqa
VERSION = (1, 0, 0)
__author__ = "odinair <odinair@odinair.xyz>"
__version__ = ".".join([str(x) for x in VERSION])
