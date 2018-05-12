import argparse
import subprocess
import os
from glob import glob
from pathlib import Path
from typing import List

root = Path(os.getcwd())
parser = argparse.ArgumentParser(usage="gen_locales.py [cog [cog ...]] [--options]")
parser.add_argument(
    "cogs",
    nargs="*",
    help="the cogs to build locales for. if no cogs are given, the current working "
    "directory is scanned for directories containing a locales directory",
)
parser.add_argument("--verbose", help="enables verbose logging", action="store_true")
parser.add_argument(
    "-p",
    "--output-dir",
    default="locales",
    help="which directory locales are stored in. defaults to `locales`",
)
parser.add_argument(
    "--docstrings", action="store_true", help="enables extracting docstrings from cogs"
)
parser.add_argument(
    "-k",
    "--keyword",
    nargs="*",
    default=[],
    help="add optional keywords to scan for, in addition to the default set (_, i18n, lazyi18n)",
)


def filter_cog_list(dirs: List[str]):
    return set(filter(lambda x: (Path(x) / args.output_dir).exists(), dirs))


def scan_dir() -> set:
    return set(
        [
            x[0].split("/")[-1]
            for x in os.walk(str(root))
            if len(x[0].replace(str(root), "").split("/")) == 2
            and (Path(x[0].split("/")[-1]) / args.output_dir).exists()
        ]
        if not args.cogs
        else args.cogs
    )


def cd(path: Path):
    if args.verbose:
        print("[verb] cd:   {}".format(str(path)))
    os.chdir(str(path))


if __name__ == "__main__":
    args = parser.parse_args()
    cogs = filter_cog_list(args.cogs or scan_dir())

    keywords = [
        item
        for sublist in [["-k", x] for x in ["lazyi18n", "i18n", *args.keyword]]
        for item in sublist
    ]

    for cog in cogs:
        print("Generating locales for cog {}".format(cog))
        cd(root / cog)

        cmd = ["python", "-m", "redgettext", "-p", args.output_dir, *keywords]

        if args.docstrings:
            cmd += ["--docstrings"]

        cmd += ["-n", *glob("**/*.py", recursive=True)]
        if args.verbose:
            print("[verb] exec: {}".format(" ".join(cmd)))
        subprocess.call(cmd)
