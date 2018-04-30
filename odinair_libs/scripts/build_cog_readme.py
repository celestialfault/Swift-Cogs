import json
from pathlib import Path
import os

root = Path(__file__).parent.parent.parent

out = root / "README.md"
# this is the repo name you instruct users to setup your repo with
repo_name = "swift-cogs"
# Anything beyond a line matching any one of these strings will be discarded and replaced with your cog list
# If this is set to None, the entire file is overwritten instead
scan_for = ["# Cogs\n", "# Cogs\r\n"]
# This is the key that will be used to retrieve a normalized cog name from
# If a cog does not contain this in their info.json, then
cog_name_key = "_cog_list_name"

# the name variable is controlled by a special '_cog_list_name' key in your cog info.json file
# if this key is not present, the value of `cog` is used instead.
# description is controlled by the `description` key, with `short` used as a fallback
cog_fmt = """<details>
<summary>{name}</summary>

{description}

#### Tags

{tags}

#### Install Cog

```
[p]cog install {repo} {cog}
[p]load {cog}
```
</details>"""

#########################################
# Don't modify anything beyond here!    #
#########################################

__version__ = '0.0.1'

cogs = set()
for f in os.walk(str(root)):
    if len(f[0].split("/")) == 1:
        continue
    cogs.add(f[0].split("/")[1])

out_strs = []
for cog in sorted(cogs):
    try:
        f = open(root / cog / "info.json")
    except IOError:
        continue
    info = json.load(f)
    f.close()
    if info.get("hidden", False) is True or info.get("type", "COG") == "SHARED_LIBRARY":
        continue

    tags = "\n".join(["🏷 **{}**  ".format(x) for x in info.get("tags", [])])\
           or "**¯\\\\_(ツ)\\_/¯** No tags are set for this cog"

    out_strs.append(cog_fmt.format(
        cog=cog,
        name=info.get(cog_name_key, cog),
        tags=tags,
        description=info.get('description', info.get('short', 'No cog description set')),
        repo=repo_name
    ))

file_str = ""
if scan_for is not None:
    with open(out) as file:
        for line in file.readlines():
            file_str += line
            if line in scan_for:
                break

with open(out, mode='w') as file:
    s = "\n\n".join(out_strs)
    file.write("{}\n{}".format(file_str, s))
    print("Wrote cog list to file {}".format(out))
