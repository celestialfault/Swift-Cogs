# This isn't a proper library file, but instead a helper script to try and compile this repository's cogs,
# while also excluding venv items. Basically, this is only useful for CircleCI testing.

from compileall import compile_dir
from pathlib import Path
import sys

PY36 = sys.version_info >= (3, 6, 0)

root_path = Path(__file__).parent.parent
cogs = [
    'botmonitor',
    'cogwhitelist',
    'misctools',
    'requirerole',
    'rndactivity',
    'rolemention',
    'starboard',
    'timedmute',
    'uinfo'
]
cogs.sort()

if PY36:
    cogs.extend([
        'logs',
        'quotes',
        'timedrole',
        'odinair_libs'
    ])


def compile_cogs():
    compiled = []
    for cog in cogs:
        compiled.append(compile_dir(str(root_path / str(cog)), force=True, ddir="__pycache__"))

    return all(compiled)


if __name__ == '__main__':
    if not PY36:
        print("Not running on Py3.6, the following modules have been implicitly skipped:\n"
              "- logs\n"
              "- quotes\n"
              "- timedrole\n"
              "- odinair_libs")
    sys.exit(int(not compile_cogs()))
