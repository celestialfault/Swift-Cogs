#!/usr/bin/env zsh

# Explanation for the above zsh shebang:
# I couldn't figure out how the fuck to get globbing to properly work in pure bash,
# as it's required for this to work as intended.

# It may be possible to get this working in bash, but I don't have any of the patience required
# to try and do so.

set -e

cogs=(cogwhitelist logs misctools quotes requirerole rndactivity rolemention starboard timedmute timedrole uinfo)

for cog in ${cogs[*]}
do
  cd ${cog}/locales
  echo "Generating locales for cog ${cog}"
  files=(../**/*.py)
  pygettext -n ${files[@]}
  cd ../..
done
