#!/usr/bin/env bash

set -e

export cogs=(cogwhitelist logs misctools quotes requirerole rndactivity rolemention starboard timedmute timedrole uinfo odinair_libs)

python3 -m compileall ${cogs[*]}
# TODO: Lower max line length to 100 once all cogs are using black code style
flake8 ${cogs[*]} --max-line-length 120 --show-source --statistics --ignore F401,W503
black --check -l 100 ${cogs[*]} || true
