import argparse
import json
import os
import random
import sys
from copy import deepcopy
import keyword
from pathlib import Path
import shutil

template_cog = r'''import discord

from redbot.core import commands
from redbot.core.bot import Red


class {cog}:
    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def punch(self, ctx: commands.Context, member: discord.Member):
        """I'll punch anyone!"""
        await ctx.send("**Pow!** And like that, {{}} is down!".format(member))
'''

template_init = r"""from .{cog_lower} import {cog}


def setup(bot):
    bot.add_cog({cog}(bot))
"""

template_info = {
    "type": "COG",
    "python_version": list(sys.version_info)[:3],
    "bot_version": [3, 0, 0],
    "tags": [],
    "description": "My new cog",
    "short": "My new cog",
}

parser = argparse.ArgumentParser(
    description="Generate a cog with a basic hello world command",
    usage="gen_cog.py [cog [cog ...]] [--options]",
)

parser.add_argument(
    "cogs",
    metavar="cog",
    type=str,
    help="the cog to generate. more than one cog can be given and will all be generated at once",
    nargs="+",
)
parser.add_argument(
    "--allow-erasing", help="overwrite an existing cog directory if it exists", action="store_true"
)

parser.add_argument("--tag", nargs="*", help="tag(s) to add to the generated info.json file")
parser.add_argument(
    "--description", default="My new cog", help="the description for the generated cog"
)
parser.add_argument(
    "--short",
    default=...,
    type=str,
    help="short description for the generated cog; defaults to the value of `--description`",
)

root = Path(os.getcwd())


def mkdir(*dirs: str, root_dir: Path = root) -> Path:
    new_dir = root_dir
    for dir_ in dirs:
        new_dir = new_dir / dir_

    print("Creating directory '{}'".format(new_dir))
    new_dir.mkdir()
    return new_dir


def touch(root_dir: Path, file_name: str) -> Path:
    file = root_dir / file_name
    print("Creating file '{}'".format(file))
    file.touch()
    return file


def write_file(root_dir: Path, file_name: str, output: str):
    with open(str(touch(root_dir, file_name)), mode="w") as f:
        f.write(output)


def create_cog(cog_name: str, *, allow_erasing: bool = False):
    if not cog_name.isidentifier():
        print("{!r} is not a valid identifier, not creating.".format(cog_name))
        return
    elif keyword.iskeyword(cog_name.lower()) or cog_name.lower() in ["async", "await"]:
        print("{!r} is a reserved Python keyword, not creating.".format(cog_name))
        return

    cog_dir = root / cog_name.lower()

    if cog_dir.exists():
        if (
            not allow_erasing
            and (
                not input(
                    "Please confirm that you wish to overwrite the following "
                    "directory (y/N): '{}'\nThis will irreversibly remove this directory, and all "
                    "files and/or directories contained within."
                    "\n".format(cog_dir)
                ).lower().startswith(
                    "y"
                )
            )
        ):
            print("Not overwriting.")
            return

        print("Removing directory '{}' and all it's contents".format(cog_dir))
        shutil.rmtree(str(cog_dir))

    cog_dir = mkdir(cog_name.lower())
    mkdir("locales", root_dir=cog_dir)

    info = deepcopy(template_info)
    info["tags"] = args.tag or []
    info["short"] = args.description if args.short is ... else args.short
    info["description"] = args.description
    info = json.dumps(info, indent=2)

    write_file(
        cog_dir, "__init__.py", template_init.format(cog_lower=cog_name.lower(), cog=cog_name)
    )
    write_file(
        cog_dir,
        "{}.py".format(cog_name.lower()),
        template_cog.format(cog=cog_name, randint=random.randint(1000, 10000000)),
    )
    write_file(cog_dir, "info.json", info)


if __name__ == "__main__":
    args = parser.parse_args()
    for cog in args.cogs:
        print("Creating cog: {}".format(cog))
        create_cog(cog, allow_erasing=args.allow_erasing)
