#!/usr/bin/env bash

set -e

export cogs=(cogwhitelist logs misctools quotes requirerole rndactivity rolemention starboard timedmute timedrole uinfo swift_libs)

python3 -m compileall ${cogs[*]}
# explanations for the following ignored checks:
# - F401:
#   Unused imports, since some <3.6 style type hints are still used in various places
# - W503:
#   Black moves binary operators onto their own lines, which is incompatible with this check
# - E203:
#   Incorrectly checks slices (such as `<list>[1 : 2]`)
flake8 ${cogs[*]} --max-line-length 100 --show-source --statistics --ignore F401,W503,E203
black --check -l 100 ${cogs[*]}
