#!/usr/bin/env bash

set -e

cd $(dirname ${0})
source ./cogs.sh
cd ../..

python3 -m compileall ${cogs[*]}
flake8 ${cogs[*]} --max-line-length 120 --show-source --statistics --ignore F401,W503
# black code style isn't enforced just yet, but is checked
black --check -l 100 ${cogs[*]} || true
