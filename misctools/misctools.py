import argparse
import asyncio
import shlex
import sys
import unicodedata
from datetime import datetime
from inspect import getsource
from textwrap import dedent
from typing import Dict, List

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import info, pagify, warning
from tabulate import tabulate

from cog_shared.odinair_libs import ConfirmMenu, formatting, td_format

_ = Translator("MiscTools", __file__)


class Arguments(argparse.ArgumentParser):

    def error(self, message):
        raise RuntimeError(message)


@cog_i18n(_)
class MiscTools:
    """A collection of small utilities that don't fit in any other cog"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def rtfs(self, ctx: commands.Context, *, command_name: str):
        """Get the source for a command or sub command"""
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(warning(_("That command doesn't exist")))
            return
        await ctx.send_interactive(pagify(dedent(getsource(command.callback))), box_lang="py")

    @commands.command()
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Get the unicode name for characters

        Up to 25 characters can be given at one time
        """
        if len(characters) > 25:
            await ctx.send_help()
            return

        def convert(c):
            return "{} \N{EM DASH} {}".format(c, unicodedata.name(c, "Name not found"))

        await ctx.send("\n".join(map(convert, characters)))

    @commands.command(hidden=True)
    @checks.is_owner()
    async def updatered(self, ctx: commands.Context, *, args: str):
        """Update Red to the latest version

        This command uses CLI-like flags to determine how to update Red.

        Available flags:
        ```
        --dev     Pulls the latest changes from GitHub
        --audio   Installs optional audio packages
        --mongo   Installs optional MongoDB packages
        ```

        These flags can also be used in shorthand fashion, meaning `-da`
        is effectively the same as passing `--dev --audio`.
        """
        parser = Arguments(add_help=False)
        parser.add_argument("-d", "--dev", action="store_true")
        parser.add_argument("-a", "--audio", action="store_true")
        parser.add_argument("-m", "--mongo", action="store_true")

        try:
            args = parser.parse_args(shlex.split(args))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
            return

        # The following is mostly ripped from the Red launcher update function
        eggs = []
        if args.audio:
            eggs.append("voice")
        if args.mongo:
            eggs.append("mongo")

        if args.dev:
            package = "git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop"
            if eggs:
                package += "#egg=Red-DiscordBot[{}]".format(", ".join(eggs))
        else:
            package = "Red-DiscordBot"
            if eggs:
                package += "[{}]".format(", ".join(eggs))

        args = [sys.executable, "-m", "pip", "install", "-U", "--process-dependency-links", package]

        confirm_str = _(
            "By continuing with this action, this I will execute the following command "
            "on your host machine:\n```\n{}\n```\n"
            "**Please note that this command has not been extensively tested, has not been "
            "reviewed by the core Red development team, and may have the potential to break your "
            "install of Red, no matter how unlikely it may be.**\n\n"
            "If you'd prefer to play it safe, cancel this action and perform the update manually, "
            "either through the Red launcher, or by executing the above command manually.\n\n"
            "**Please confirm that you wish to continue with this action.**"
        ).format(
            # the full executable path is masked to hide the root directory,
            # since some users may use a venv in a directory that they wouldn't
            # want to reveal through an update command, such as on Windows
            # with a real name as their account name
            " ".join(["python"] + args[1:])
        )

        if not await ConfirmMenu(ctx, message=warning(confirm_str)):
            await ctx.send(info(_("Update aborted.")))
            return

        tmp = await ctx.send(
            info(
                _(
                    "Updating Red...\n\nThis may take a while, so go get yourself a cup of coffee, "
                    "tea, or whatever other choice of beverage you may prefer."
                )
            )
        )
        async with ctx.typing():
            p = await asyncio.create_subprocess_exec(*args, stdin=None, loop=self.bot.loop)
            await p.wait()

        await tmp.delete()

        if p.returncode == 0:
            await ctx.send(
                _("Red has been updated. Please restart the bot for any updates to take affect.")
            )
        else:
            await ctx.send(
                _("Something went wrong while updating. Please attempt an update manually.")
            )

    @commands.command(aliases=["pingt"])
    async def pingtime(self, ctx: commands.Context):
        """Get the time it takes the bot to respond to a command

        This is by no means fully accurate, and should be treated similarly to rough estimate

        Time to command execution means how long it took for the bot to receive the command message
        and execute the command
        """
        time_to_execution = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True)
        now = datetime.utcnow()
        await ctx.trigger_typing()
        time_to_typing = td_format(datetime.utcnow() - now, milliseconds=True)
        full_round_trip = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True)
        await ctx.send(
            _(
                "\N{TABLE TENNIS PADDLE AND BALL} Pong!\n"
                "Time to command execution: {}\n"
                "Typing indicator: {}\n\n"
                "Full round trip: {}"
            ).format(
                time_to_execution, time_to_typing, full_round_trip
            )
        )

    @commands.group(aliases=["snowflake"], invoke_without_command=True)
    async def snowflaketime(self, ctx: commands.Context, *snowflakes: int):
        """Retrieve when one or more snowflake IDs were created at"""
        if not snowflakes:
            await ctx.send_help()
            return
        strs = []
        for snowflake in snowflakes:
            snowflake_time = discord.utils.snowflake_time(snowflake)
            strs.append(
                "{}: `{}` \N{EM DASH} {}".format(
                    snowflake,
                    snowflake_time.strftime("%A %B %d, %Y at %X UTC"),
                    td_format(snowflake_time - datetime.utcnow(), append_str=True),
                )
            )
        await ctx.send_interactive(pagify("\n".join(strs)))

    @snowflaketime.command(name="delta")
    async def snowflake_delta(self, ctx: commands.Context, start: int, end: int):
        """Get the time difference between two snowflake IDs"""
        start, end = (discord.utils.snowflake_time(start), discord.utils.snowflake_time(end))
        now = datetime.utcnow()

        await ctx.send(
            _(
                "**Starting snowflake:** {start[0]} \N{EM DASH} `{start[1]}`\n"
                "**Ending snowflake:** {end[0]} \N{EM DASH} `{end[1]}`\n\n"
                "**Time difference:** {difference}"
            ).format(
                start=[
                    td_format(start - now, append_str=True),
                    start.strftime("%A %B %d, %Y at %X UTC"),
                ],
                end=[td_format(end - now, append_str=True), end.strftime("%A %B %d, %Y at %X UTC")],
                difference=td_format(end - start),
            )
        )

    @commands.command(aliases=["permbd"])
    @commands.guild_only()
    async def permissionbreakdown(self, ctx: commands.Context, *, member: discord.Member = None):
        """Break down the permissions for a given member

        This command does not take channel overrides into account, and only
        checks for server role permissions.

        If more than three roles grant a single permission, only the first three are shown
        for each permission.
        """
        member = member or ctx.author
        perms = {x: [] for x, y in discord.Permissions()}  # type: Dict[str, List[discord.Role]]
        for role in reversed(member.roles):
            for perm, value in role.permissions:
                if value is False:
                    continue
                perms[perm].append(role)

        await ctx.send_interactive(
            pagify(
                "{}\n\n{}".format(
                    _("Permission Breakdown").center(50),
                    tabulate(
                        [
                            [
                                x,
                                _("Granted by default role")
                                if ctx.guild.default_role in y
                                else ", ".join(str(v) for v in y[:3])
                                or _("Not granted by any role"),
                            ]
                            for x, y in {
                                formatting.permissions.get(x, lambda: x)(): y
                                for x, y in perms.items()
                            }.items()
                        ],
                        headers=[_("Permission"), _("Granted By")],
                        tablefmt="psql",
                    ),
                )
            ),
            box_lang="",
        )
