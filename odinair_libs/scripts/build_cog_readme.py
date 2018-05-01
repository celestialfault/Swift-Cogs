import json
from pathlib import Path
import os

__version__ = "0.0.1"

root = Path(__file__).parent.parent.parent

out = root / "README.md"
# this is the repo name you instruct users to setup your repo with
repo_name = "swift-cogs"
# Anything beyond a line matching any one of these strings will be discarded and replaced
# with your cog list. If this is set to a falsy value like None, the entire file is overwritten
# instead.
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

### Requirements

{requirements}

### Install Cog

```
[p]cog install {repo} {cog}
[p]load {cog}
```
</details>"""


def parse_cogs():
    cogs = set()
    for folder in os.walk(str(root)):
        if len(folder[0].split("/")) == 1:
            continue
        cogs.add(folder[0].split("/")[1])

    for cog in sorted(cogs):
        try:
            finfo = open(root / cog / "info.json")
        except IOError:
            continue
        info = json.load(finfo)
        finfo.close()
        if info.get("hidden", False) is True or info.get("type", "COG") == "SHARED_LIBRARY":
            continue

        cog_requirements = [
            "- [{}]({})".format(k, v) for k, v in info.get("required_cogs", {}).items()
        ]
        package_requirements = ["- `{}` library".format(x) for x in info.get("requirements", [])]
        requirements = "\n".join(
            [*cog_requirements, *package_requirements]
        ) or "This cog has no requirements."

        yield cog_fmt.format(
            cog=cog,
            name=info.get(cog_name_key, cog),
            requirements=requirements,
            description=info.get("description", info.get("short", "No cog description set")),
            repo=repo_name,
        )


def read_file():
    file_str = ""
    if scan_for:
        with open(out) as file:
            for line in file.readlines():
                file_str += line
                if line in scan_for:
                    break

    return file_str


if __name__ == "__main__":
    old = read_file()
    with open(out, mode="w") as f:
        s = "\n\n".join(parse_cogs())
        if old:
            data = "{}\n{}".format(old, s)
        else:
            data = s

        f.write(data)
        print("Wrote cog list to file {}".format(out))
