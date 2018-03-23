from compileall import compile_dir
from pathlib import Path
import sys

root_path = Path(__file__).parent.parent
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


def compile_cogs():
    compiled = []
    for cog in cogs:
        compiled.append(compile_dir(root_path / str(cog), force=True, ddir="__pycache__"))

    return all(compiled)


if __name__ == '__main__':
    if not compile_cogs():
        sys.exit(1)
