# This is only around to manually filter out items in CircleCI test logs,
# through means of a very rudimentary whitelist

from compileall import compile_dir
from pathlib import Path
import sys

cogs = [
    'botmonitor',
    'cogwhitelist',
    'logs',
    'misctools',
    'odinair_libs',
    'quotes',
    'requirerole',
    'rndactivity',
    'rolemention',
    'starboard',
    'timedrole',
    'timedmute',
    'uinfo'
]
cogs.sort()

compiled = []
for cog in cogs:
    compiled.append(compile_dir(Path(__file__).parent / str(cog), force=True, ddir="__pycache__"))

if not all(compiled):
    sys.exit(1)
