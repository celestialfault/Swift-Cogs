#!/usr/bin/env bash

set -e

export cogs=(cogwhitelist logs misctools quotes requirerole rndactivity rolemention starboard timedmute timedrole uinfo swift_libs)

python3 -m compileall ${cogs[*]}
flake8 ${cogs[*]} --max-line-length 100 --show-source --statistics --ignore F401,W503
black --check -l 100 ${cogs[*]}
