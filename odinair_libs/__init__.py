"""
Shared library for all my cogs
"""

from .commands import *  # noqa
from .menus import *  # noqa
from .time import *  # noqa
from .converters import *  # noqa
from .checks import *  # noqa
from .formatting import *  # noqa
try:
    from .asynctools import *  # noqa
except (SyntaxError, ImportError):
    # if this try/catch isn't included, then anyone attempting to load any cogs on 3.5 that uses this shared library
    # will instead be the proud owner a very helpful SyntaxError, and a very non-functional cog.
    CallableAsyncGenerator = None

    # noinspection PyUnusedLocal
    async def async_gen_to_list(*args, **kwargs):
        raise RuntimeError('not running on python 3.6')

__author__ = "odinair <odinair@odinair.xyz>"
