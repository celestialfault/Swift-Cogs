#!/usr/bin/env zsh

# Explanation for the above zsh shebang:
# I couldn't figure out how the fuck to get globbing to properly work in pure bash,
# as it's required for this to work as intended.

# It may be possible to get this working in bash, but I don't have any of the patience
# that would be required to try and do so, nor the desire to copy/paste the same
# few dozen lines several times with minor changes.

set -e

cd $(dirname ${0})
source ./cogs.sh
cd ../..

if ! where redgettext &>/dev/null; then
    echo Installing redgettext...
    pip install -U redgettext
fi

for cog in ${cogs[*]}
do
  cd ${cog}/locales
  echo "Generating locales for cog ${cog}"
  redgettext $@ -k i18n -n ../**/*.py
  cd ../..
done
