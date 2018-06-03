import argparse
import asyncio
import shlex
import sys
import unicodedata
from datetime import datetime, timedelta
from inspect import getsource
from statistics import mean
from textwrap import dedent
from typing import Dict, List, Optional, Union

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import info, pagify, warning, error

from cog_shared.swift_libs import (
    confirm,
    td_format,
    PaginatedMenu,
    Page,
    format_permission,
    chunks,
    mention,
    resolve_any,
)

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
        try:
            source = pagify(dedent(getsource(command.callback)))
        except OSError:
            await ctx.send(
                error(
                    _(
                        "Failed to retrieve the source for the given command"
                        " (was it created in an eval statement?)"
                    )
                )
            )
            return
        await ctx.send_interactive(source, box_lang="py")

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

        **Available flags:**
        (these flags can also be used in shorthand fashion, meaning `-am`
        is effectively the same as passing `--audio --mongo`)

        **--audio|voice** — Installs optional audio packages
        **--mongo** — Installs optional MongoDB packages

        **Advanced options:**
        **--dev** — Pulls the latest changes from GitHub
        """
        parser = Arguments(add_help=False)
        parser.add_argument("-d", "--dev", action="store_true")
        parser.add_argument("-a", "--audio", action="store_true")
        parser.add_argument("-v", "--voice", action="store_true")  # alias for --audio
        parser.add_argument("-m", "--mongo", action="store_true")

        try:
            args = parser.parse_args(shlex.split(args))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
            return

        # The following is mostly ripped from the Red launcher update function
        eggs = []
        if args.audio or args.voice:
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

        if not await confirm(
            ctx,
            content=warning(
                _(
                    "By continuing with this action, this I will execute the following command "
                    "on your host machine:\n```\n{}\n```\n"
                    "**Please note that this command has not been extensively tested, has not been "
                    "reviewed by the core Red development team, and may have the potential to"
                    " break your install of Red, no matter how unlikely it may be.**\n\n"
                    "If you'd prefer to play it safe, cancel this action and perform the"
                    " update manually, either through the Red launcher, or by executing the above"
                    " command manually.\n\n"
                    "**Please confirm that you wish to continue with this action.**"
                ).format(
                    # the full executable path is masked to hide the root directory,
                    # since some users may use a venv in a directory that they wouldn't
                    # want to reveal through an update command, such as on Windows
                    # with a real name as their account name
                    " ".join(["python"] + args[1:])
                )
            ),
        ):
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
                _("Red has been updated. Please restart the bot for the updates to take affect.")
            )
        else:
            await ctx.send(
                _(
                    "Something went wrong while updating. Check your logs,"
                    " and attempt an update manually."
                )
            )

    @commands.command(aliases=["pingt", "latency"])
    async def pingtime(self, ctx: commands.Context):
        """Get the bot's latency to Discord"""
        if self.bot.shard_count > 1:
            latency = dict(self.bot.latencies)
            await ctx.send(
                _(
                    "**Server shard latency** is {local}.\n\n"
                    "**Global latency:**\n"
                    "\N{BULLET} **Average:** {global_avg}\n"
                    "\N{BULLET} **Max:** {global_max}"
                ).format(
                    local=td_format(
                        timedelta(seconds=latency[ctx.guild.shard_id]), milliseconds=True
                    ),
                    global_avg=td_format(
                        timedelta(seconds=mean(latency.values())), milliseconds=True
                    ),
                    global_max=td_format(
                        timedelta(seconds=max(latency.values())), milliseconds=True
                    ),
                )
            )

        else:
            await ctx.send(
                _("**Current latency:** {latency}").format(
                    latency=td_format(timedelta(seconds=self.bot.latency), milliseconds=True)
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
    async def snowflake_delta(self, ctx: commands.Context, starting: int, ending: int):
        """Get the time difference between two snowflake IDs"""
        starting, ending = (
            discord.utils.snowflake_time(starting),
            discord.utils.snowflake_time(ending),
        )
        now = datetime.utcnow()

        await ctx.send(
            _(
                "**Starting snowflake:** {start_delta} \N{EM DASH} `{start_date}`\n"
                "**Ending snowflake:** {end_delta} \N{EM DASH} `{end_date}`\n\n"
                "**Time difference:** {difference}"
            ).format(
                start_delta=td_format(starting - now, append_str=True),
                start_date=starting.strftime("%A %B %d, %Y at %X UTC"),
                end_delta=td_format(ending - now, append_str=True),
                end_date=ending.strftime("%A %B %d, %Y at %X UTC"),
                difference=td_format(ending - starting),
            )
        )

    @commands.command(aliases=["permbd"])
    @commands.guild_only()
    async def permissionbreakdown(
        self, ctx: commands.Context, member: discord.Member = None, channel=None
    ):
        """Break down the permissions for a given member

        If more than three roles grant a single permission, only the member's top three
        roles are shown for each permission.
        """
        member = member or ctx.author
        if channel is not None:
            channel = await resolve_any(
                ctx,
                channel,
                commands.TextChannelConverter,
                commands.VoiceChannelConverter,
                commands.CategoryChannelConverter,
            )
        else:
            channel = ctx.channel
        perms: Dict[str, List[discord.Role]] = {
            x: [r for r in reversed(member.roles) if getattr(r.permissions, str(x), False) is True]
            for x, y in discord.Permissions()
        }

        def converter(pg: Page):
            embed = discord.Embed(
                colour=ctx.me.colour,
                title=_("Permission Breakdown"),
                description=_("Displaying permissions for member {}").format(member.mention),
            )

            # noinspection PyShadowingNames
            for perm, roles in pg.data:
                roles = [mention(x) for x in roles[:3]]
                if not roles:
                    value = [
                        _("This permission is not granted by any of {}'s roles").format(
                            member.mention
                        )
                    ]
                else:
                    value = [
                        " \N{EM DASH} ".join(
                            [
                                (
                                    _("Granted by {} roles")
                                    if len(roles) != 1
                                    else _("Granted by {} role")
                                ).format(len(roles)),
                                ", ".join(roles),
                            ]
                        )
                    ]

                overwrites: Dict[Union[discord.Member, discord.Role], Optional[bool]] = {
                    x: getattr(y, perm, None)
                    for x, y in channel.overwrites
                    if x == member or x in member.roles and getattr(y, perm, None) is not None
                }
                if overwrites:
                    granted = [x for x, y in overwrites.items() if y is True]
                    denied = [x for x, y in overwrites.items() if y is False]
                    if granted:
                        value.append(
                            " ".join(
                                [
                                    (
                                        _("Granted by {} overwrites for \N{EM DASH}")
                                        if len(granted) != 1
                                        else _("Granted by {} overwrite for \N{EM DASH}")
                                    ).format(len(granted)),
                                    ", ".join(mention(x) for x in granted[:3]),
                                ]
                            )
                        )
                    if denied:
                        value.append(
                            " ".join(
                                [
                                    (
                                        _("Denied by {} overwrites for \N{EM DASH}")
                                        if len(denied) != 1
                                        else _("Denied by {} overwrite for \N{EM DASH}")
                                    ).format(len(denied)),
                                    ", ".join(mention(x) for x in denied[:3]),
                                ]
                            )
                        )

                embed.add_field(name=format_permission(perm), value="\n".join(value), inline=False)

            return embed.set_footer(
                text=_("Page {current} out of {total}").format(current=pg.current, total=pg.total)
            )

        await PaginatedMenu(
            ctx=ctx,
            pages=list(chunks(list(perms.items()), round(len(perms) / 4))),
            converter=converter,
            wrap_around=True,
        )
