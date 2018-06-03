"""
Shared library for all my cogs
"""
__author__ = "odinair <odinair@odinair.xyz>"

from .checks import *  # noqa
from .commands import *  # noqa
from .formatting import *  # noqa
from .helpers import *  # noqa
from .i18n import LazyString, LazyTranslator, to_lazy_translator, fi18n  # noqa
from .menus import *  # noqa
from .menus_legacy import *  # noqa
from .time import *  # noqa

__import__("logging").getLogger("red.swift_libs").warn(
    "Hi! It seems you're using my GitHub cog repository.\n"
    "I've since moved these to GitLab, and the cogs from this repository"
    " won't be updated anymore.\n\n"
    "If you'd like to continue getting updates, please update your bot "
    "to use this git repository instead: https://gitlab.com/odinair/Swift-Cogs\n\n"
    "Thanks!~ \N{PURPLE HEART}\n  ~ odinair"
)
