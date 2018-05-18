import json
import re
from pathlib import Path
import os
import argparse
from jinja2 import Template

if __name__ != "__main__":
    raise ImportError("importing this module is not supported")

__version__ = "1.0.0"

root = Path(str(os.getcwd()))
script_root = Path(__file__).parent


def absolute_path(path: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        path = script_root / str(path)
    return path


parser = argparse.ArgumentParser(
    description="Generate a fancy cog list in your repository's README file"
)
parser.add_argument(
    "cogs",
    nargs="*",
    help="the cogs to generate a help list for. if no cogs are given, "
    "the current directory is scanned instead",
)

parser.add_argument(
    "--config", default="gen_readme.json", help="manually set a config file location"
)

args = parser.parse_args()


###########################################


with open(str(absolute_path(args.config)), mode="r") as f:
    config = json.load(f)

out = Path(config["output"]).resolve()
repo_name = config["repo_name"]

if config["overwrite"] is False:
    scan_for = [i for s in [[x + "\n", x + "\r\n"] for x in config["scan_for"]] for i in s]
else:
    scan_for = []

cog_name_key = config["cog_name_key"]

with open(str(absolute_path(config["template"])), mode="r") as template_f:
    template = Template(template_f.read())


###########################################


class Cog:

    def __init__(self, raw_name: str, raw_info: dict):
        self.info = raw_info
        self.raw_name = raw_name

    @property
    def description(self):
        return self.info.get("description")

    @property
    def short(self):
        return self.info.get("short")

    @property
    def tags(self):
        return self.info.get("tags", [])

    @property
    def name(self):
        return self.info.get(cog_name_key, self.raw_name)

    @property
    def requirements(self):
        return [{"name": x} for x in self.info.get("requirements", [])] + [
            {"name": x, "repo_url": y} for x, y in self.info.get("required_cogs", {}).items()
        ]


def parse_requirements(info: dict):
    for req in info.get("requirements", []):
        yield {"name": req}

    for req, url in info.get("required_cogs", {}).items():
        yield {"name": req, "repo_url": url}


def parse_cogs():
    cogs = set(
        [
            x[0].split("/")[-1]
            for x in os.walk(str(root))
            if len(x[0].replace(str(root), "").split("/")) == 2
        ]
        if not args.cogs
        else args.cogs
    )

    cog_info = {}

    for cog in sorted(cogs):
        print("Retrieving info for cog {}".format(cog))
        try:
            with open(root / cog / "info.json") as finfo:
                info = json.load(finfo)
        except FileNotFoundError:
            print("  {} has no info.json file, skipping".format(cog))
            continue
        else:
            if info.get("hidden", False) is True or info.get("type", "COG") == "SHARED_LIBRARY":
                print("  {} is marked as hidden; skipping.".format(cog))
                continue
            cog_info[cog] = info

    return re.sub(
        r"\n(\n){2,}",
        "\n\n",
        template.render(
            cogs=[Cog(name, info) for name, info in cog_info.items()], repo=repo_name
        ).rstrip(),
    ).rstrip()


def read_file():
    file_str = ""
    if scan_for:
        with open(out) as file:
            for line in file.readlines():
                file_str += line
                if line in scan_for:
                    break

    return file_str


old = read_file()
with open(out, mode="w") as f:
    cog_readme = parse_cogs()
    if old:
        data = "".join([old, cog_readme])
    else:
        data = cog_readme

    f.write(data)
    print("Wrote cog list to file {}".format(out))
