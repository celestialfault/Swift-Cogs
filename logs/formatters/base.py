import discord
import asyncio

from datetime import datetime, timedelta

from redbot.core.bot import Red
from redbot.core import Config
from redbot.core.utils.chat_formatting import escape

from typing import Iterable

from .utils import td_format, difference, normalize


def setup(_bot: Red, _config: Config):
    global bot
    bot = _bot
    global config
    config = _config


class FormatterBase:
    def __init__(self, guild: discord.Guild):
        self.guild = guild

    @property
    def config(self):
        return config.guild(self.guild)

    async def log_channel(self, group: str):
        return bot.get_channel(await self.config.log_channels.get_attr(group))

    async def send_log_message(self, log_group: str, log_type: str, **kwargs):
        log_func = "{}_{}".format(log_group, log_type)
        try:
            formatter = self.__getattribute__(log_func)
        except AttributeError:
            return
        if not formatter:
            return
        log_channel = await self.log_channel(log_group)
        if not log_channel:
            return

        try:
            data = await formatter(**kwargs) if asyncio.iscoroutinefunction(formatter) else formatter(**kwargs)
        except KeyError:
            return
        if data is None:
            return

        if not isinstance(data, Iterable) and not isinstance(data, discord.Embed) and not isinstance(data, str):
            raise ValueError("Formatter returned %s, expected Iterable, Embed or str" % data.__class__.__name__)

        if not isinstance(data, Iterable):
            data = [data]

        for item in data:
            if not item:
                continue
            if isinstance(item, discord.Embed):
                try:
                    await log_channel.send(embed=item)
                except discord.Forbidden:
                    return
            elif isinstance(item, str):
                await log_channel.send(item)
            else:
                raise ValueError("Found an unexpected %s, expected Embed or str" % item.__class__.__name__)

    def format(self, title: str, text: str, *, emoji: str, colour: discord.Colour, member: discord.Member=None,
               timestamp: datetime=None):
        raise NotImplementedError

    async def members_join(self, member: discord.Member):
        account_age = td_format(member.created_at - member.joined_at)
        if not account_age:
            account_age = "brand new"
        else:
            account_age = account_age + " old"
        return [self.format("Member joined", "**{}** joined the server\nAccount is {}".format(
                escape(str(member), formatting=True, mass_mentions=True), account_age),
            emoji="\N{WAVING HAND SIGN}", colour=discord.Colour.green(), member=member)]

    async def members_leave(self, member: discord.Member):
        return [self.format("Member left", "**{}** left after being a member for {}".format(
                escape(str(member), formatting=True, mass_mentions=True),
                td_format(member.joined_at - datetime.utcnow())),
            emoji="\N{DOOR}", colour=discord.Colour.red(), member=member)]

    async def members_update(self, before: discord.Member, after: discord.Member):
        settings = await self.config.members.update()
        msgs = []
        if (before.name != after.name) and settings["name"]:
            msgs.append(self.format("Member updated", "Member **{}** changed their name to **{}**".format(
                escape(str(before), formatting=True, mass_mentions=True),
                escape(str(after), formatting=True, mass_mentions=True)
            ), emoji="\N{MEMO}", colour=discord.Colour.blurple(), member=after))
        if (before.nick != after.nick) and settings["nickname"]:
            msgs.append(self.format("Member updated", "Member **{}**'s nickname has been changed to to **{}**".format(
                escape(str(after), formatting=True, mass_mentions=True),
                escape(after.nick, formatting=True, mass_mentions=True)
            ), emoji="\N{MEMO}", colour=discord.Colour.blurple(), member=after))
        if (before.roles != after.roles) and settings["roles"]:
            diff = difference(before.roles, after.roles, check_val=False)
            added = diff["added"]
            removed = diff["removed"]
            if len(added) > 0:
                msgs.append(self.format("Member roles updated", "Member **{}** gained role{} **{}**".format(
                    escape(str(after), mass_mentions=True, formatting=True),
                    "s" if len(added) > 1 else "",
                    escape(", ".join([x.name for x in added]), formatting=True, mass_mentions=True)
                ), emoji="\N{BUSTS IN SILHOUETTE}", colour=discord.Colour.green(), member=after))
            if len(removed) > 0:
                msgs.append(self.format("Member roles updated", "Member **{}** lost role{} **{}**".format(
                    escape(str(after), mass_mentions=True, formatting=True),
                    "s" if len(removed) > 1 else "",
                    escape(", ".join([x.name for x in removed]), formatting=True, mass_mentions=True)
                ), emoji="\N{BUSTS IN SILHOUETTE}", colour=discord.Colour.orange(), member=after))
        return msgs

    async def guild_update(self, before: discord.Guild, after: discord.Guild):
        if after.unavailable or before.unavailable:
            # Don't do anything with guilds that are or were marked as unavailable
            return []
        settings = await self.config.guild()
        msgs = []
        if (before.name != after.name) and settings["name"]:  # Guild name
            msgs.append(self.format("Guild updated", "Guild name changed to **{}**".format(
                escape(after.name, formatting=True, mass_mentions=True)),
                                    emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.verification_level != after.verification_level) and settings["verification"]:  # Verification level
            msgs.append(self.format("Guild updated", "Guild verification level changed to **{}**".format(
                normalize(str(after.verification_level), title_case=True)
            ), emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.owner_id != after.owner_id) and settings["owner"]:  # Ownership transfer
            msgs.append(self.format("Guild ownership transferred", "**Guild ownership has been transferred to {}**"
                                    .format(escape(str(after.owner), mass_mentions=True, formatting=True)
                                            ), emoji="\N{KEY}", colour=discord.Colour.blurple()))
        if (before.mfa_level != after.mfa_level) and settings["2fa"]:  # 2FA requirement
            if after.mfa_level == 1:
                msgs.append(self.format("Guild updated", "**2FA requirement enabled for administrative permissions**",
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
            else:
                msgs.append(self.format("Guild updated", "**2FA requirement disabled for administrative permissions**",
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.afk_timeout != after.afk_timeout) and settings["afk"]:
            delta = timedelta(seconds=after.afk_timeout)
            msgs.append(self.format("Guild updated", "AFK timeout set to {}".format(td_format(delta)),
                                    emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.afk_channel != after.afk_channel) and settings["afk"]:
            if after.afk_channel:
                msgs.append(self.format("Guild updated", "AFK channel set to {}".format(after.afk_channel.mention),
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
            else:
                msgs.append(self.format("Guild updated", "AFK channel unset",
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        return msgs

    async def channels_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        return [self.format("Channel created", "Channel {} has been created".format(channel.name),
                            emoji="\N{LOWER LEFT BALLPOINT PEN}", colour=discord.Colour.green())]

    async def channels_delete(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        return [self.format("Channel deleted", "Channel {} has been deleted".format(channel.name),
                            emoji="\N{WASTEBASKET}", colour=discord.Colour.red())]

    async def channels_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        settings = await self.config.channels.update()
        msgs = []
        # shh pycharm, there's no need to be upset
        # noinspection PyUnresolvedReferences
        if (before.name != after.name) and settings["name"]:
            # noinspection PyUnresolvedReferences
            msgs.append(self.format("Channel updated", "Channel **{}** name changed to **{}**".format(
                escape(before.name, formatting=True, mass_mentions=True),
                escape(after.name, formatting=True, mass_mentions=True)
            ), emoji="\N{NAME BADGE}", colour=discord.Colour.blurple()))
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if (before.topic != after.topic) and settings["topic"]:
                msgs.append(self.format("Channel updated", "Channel **{}** topic changed to:\n**{}**".format(
                    escape(after.name, formatting=True, mass_mentions=True),
                    escape(after.topic, formatting=True, mass_mentions=True)
                ), emoji="\N{NEWSPAPER}", colour=discord.Colour.blurple()))
        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if (before.bitrate != after.bitrate) and "bitrate" in settings and settings["bitrate"]:
                msgs.append(self.format("Channel updated", "Channel **{}** bitrate changed to {}".format(
                    escape(after.name, formatting=True, mass_mentions=True),
                    str(after.bitrate)[:-3] + " kbps"
                ), emoji="\N{MEMO}", colour=discord.Colour.blurple()))
            if (before.user_limit != after.user_limit) and "user_limit" in settings and settings["user_limit"]:
                msgs.append(self.format("Channel updated", "User limit for channel **{}** has been {}".format(
                    escape(after.name, formatting=True, mass_mentions=True),
                    "changed to " + after.user_limit
                    if after.user_limit > 0 else "removed"
                ), emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if before.category != after.category:
            msgs.append(self.format("Channel updated", "Channel **{}** moved to category **{}**".format(
                escape(after.name, formatting=True, mass_mentions=True),
                escape(after.category.name if after.category else "Uncategorized", mass_mentions=True, formatting=True)),
                                    emoji="\N{CLASSICAL BUILDING}", colour=discord.Colour.blurple()))
        return msgs

    async def roles_update(self, before: discord.Role, after: discord.Role):
        settings = await self.config.roles.update()
        msgs = []
        if (before.name != after.name) and settings["name"]:
            msgs.append(self.format("Role updated", "Role **{}** name changed to **{}**".format(
                escape(before.name, formatting=True, mass_mentions=True),
                escape(after.name, formatting=True, mass_mentions=True)
            ), emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.position != after.position) and settings["position"]:
            msgs.append(self.format("Role updated", "Role **{}** moved position to {}".format(escape(after.name,
                                                                                                     mass_mentions=True,
                                                                                                     formatting=True),
                                                                                              after.position),
                                    emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.hoist != after.hoist) and settings["hoist"]:
            msgs.append(self.format("Role updated", "Role **{}** is {}".format(escape(after.name,
                                                                                      formatting=True,
                                                                                      mass_mentions=True),
                                                                               "now hoisted" if after.hoist
                                                                               else "no longer hoisted"),
                                    emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.mentionable != after.mentionable) and settings["mention"]:
            msgs.append(self.format("Role updated", "Role **{}** is {}".format(escape(after.name,
                                                                                      formatting=True,
                                                                                      mass_mentions=True),
                                                                               "now mentionable" if after.mentionable
                                                                               else "no longer mentionable"),
                                    emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.permissions.value != after.permissions.value) and settings["permissions"]:
            diff = difference(before.permissions, after.permissions, check_val=True)
            added = diff["added"]
            removed = diff["removed"]
            if len(added) > 0:
                msgs.append(self.format("Role updated", "Permissions granted to role **{}**:\n\n{}".format(
                    escape(after.name, mass_mentions=True, formatting=True), ", ".join([normalize(x,
                                                                                                  title_case=True,
                                                                                                  guild="server")
                                                                                        for x in added])),
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
            if len(removed) > 0:
                msgs.append(self.format("Role updated", "Permissions revoked from role **{}**:\n\n{}".format(
                    escape(after.name, mass_mentions=True, formatting=True), ", ".join([normalize(x,
                                                                                                  title_case=True,
                                                                                                  guild="server")
                                                                                        for x in removed])),
                                        emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        if (before.colour != after.colour) and "colour" in settings and settings["colour"]:
            msgs.append(self.format("Role updated", "Role **{}** colour changed to `{}`".format(
                escape(after.name, formatting=True, mass_mentions=True),
                str(after.colour)
            ), emoji="\N{MEMO}", colour=discord.Colour.blurple()))
        return msgs

    async def roles_create(self, role: discord.Role):
        return [self.format("Role created", "Role **{}** created".format(escape(role.name, mass_mentions=True,
                                                                                formatting=True)),
                            emoji="\N{LOWER LEFT BALLPOINT PEN}", colour=discord.Colour.green())]

    async def roles_delete(self, role: discord.Role):
        return [self.format("Role deleted", "Role **{}** has been deleted".format(escape(role.name, mass_mentions=True,
                                                                                         formatting=True)),
                            emoji="\N{WASTEBASKET}", colour=discord.Colour.red())]

    async def messages_delete(self, message: discord.Message):
        if message.author.bot:  # don't log messages from bots
            return []
        attach = ""
        if message.attachments:
            attach = "\n\n**Message attachments:**\n<{}>".format(message.attachments[0].proxy_url)
        return [self.format("Message deleted", "**Author:** {}\n\n**Content:**\n{}{}".format(
            escape(str(message.author), formatting=True, mass_mentions=True),
            escape(message.content, mass_mentions=True),
            attach),
                            emoji="\N{WASTEBASKET}", colour=discord.Colour.red(), member=message.author)]

    # noinspection PyUnusedLocal
    async def messages_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot:  # don't log messages from bots
            return []
        return [self.format("Message edited", "**Author:** {}\n\n**New content:**\n{}".format(
            escape(str(after.author), formatting=True, mass_mentions=True),
            escape(after.content, mass_mentions=True)),
                            emoji="\N{MEMO}", colour=discord.Colour.blurple(), member=after.author)]

    async def voice_update(self, before: discord.VoiceState, after: discord.VoiceState, member: discord.Member):
        settings = await self.config.voice()
        msgs = []
        if before.channel != after.channel:
            if before.channel is not None and after.channel is not None:  # Switch channel
                if settings["switch"]:
                    msgs.append(self.format("Voice status updated",
                                            "Member **{}** switched voice channels, from **{}** to **{}**".format(
                                                escape(str(member), formatting=True, mass_mentions=True),
                                                escape(before.channel.name, formatting=True, mass_mentions=True),
                                                escape(after.channel.name, formatting=True, mass_mentions=True)
                                            ), emoji="\N{SPEAKER}", colour=discord.Colour.greyple()))
            elif before.channel is not None and after.channel is None:  # Left voice
                if settings["leave"]:
                    msgs.append(self.format("Voice status updated", "Member **{}** left voice channel **{}**".format(
                        escape(str(member), formatting=True, mass_mentions=True),
                        escape(after.channel.name, formatting=True, mass_mentions=True)
                    ), emoji="\N{SPEAKER}", colour=discord.Colour.greyple()))
            elif before.channel is None and after.channel is not None:  # Joined voice
                if settings["join"]:
                    msgs.append(self.format("Voice status updated", "Member **{}** joined voice channel **{}**".format(
                        escape(str(member), formatting=True, mass_mentions=True),
                        escape(after.channel.name, formatting=True, mass_mentions=True)
                    ), emoji="\N{SPEAKER}", colour=discord.Colour.greyple()))
        if (before.self_deaf != after.self_deaf) and settings["selfdeaf"]:
            msgs.append(self.format("Voice status updated", "Member **{}** is {}".format(
                escape(str(member), formatting=True, mass_mentions=True),
                "no longer self-deafened" if not after.self_deaf else "now self-deafened"
            ), emoji="\N{SPEAKER}", colour=discord.Colour.greyple()))
        if (before.self_mute != after.self_mute) and settings["selfmute"]:
            msgs.append(self.format("Voice status updated", "Member **{}** is {}".format(
                escape(str(member), formatting=True, mass_mentions=True),
                "no longer self-muted" if not after.self_mute else "now self-muted"
            ), emoji="\N{SPEAKER}", colour=discord.Colour.greyple()))
        if (before.deaf != after.deaf) and settings["serverdeaf"]:
            msgs.append(self.format("Voice status updated", "Member **{}** is {}".format(
                escape(str(member), formatting=True, mass_mentions=True),
                "no longer server deafened" if not after.deaf else "now server deafened"
            ), emoji="\N{SPEAKER}", colour=discord.Colour.orange()))
        if (before.mute != after.mute) and settings["servermute"]:
            msgs.append(self.format("Voice status updated", "Member **{}** is {}".format(
                escape(str(member), formatting=True, mass_mentions=True),
                "no longer server muted" if not after.mute else "now server muted"
            ), emoji="\N{SPEAKER}", colour=discord.Colour.orange()))
        return msgs
