import asyncio
import re

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import escape, warning

from cog_shared.odinair_libs import cmd_help, tick

_ = Translator("RoleMention", __file__)


@cog_i18n(_)
class RoleMention:
    MENTION_REGEX = re.compile(r"{{mention role: ?@?(?P<NAME>[\W\w]+)}}", re.IGNORECASE)

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21312234, force_registration=True)
        self.config.register_guild(roles=[])

    async def _can_mention(self, message: discord.Message):
        try:
            guild = message.guild  # type: discord.Guild
            if guild is None:
                return False
        except AttributeError:
            return False

        try:
            me = guild.me
            my_cperms = message.channel.permissions_for(me)
            my_gperms = me.guild_permissions
            return all(
                [
                    not message.author.bot,
                    my_gperms.manage_roles,
                    my_cperms.send_messages,
                    any(
                        [
                            guild.me.guild_permissions.manage_roles,
                            await self.bot.is_admin(message.author),
                        ]
                    ),
                ]
            )
        except AttributeError:
            # This can happen as a result of Red.is_admin() being passed a user object, instead
            # of a member. I'm not sure how or why, but it somehow can happen.
            # Of course, this is purely going off of my system logs.
            # So I don't know how it happened, and by extension I don't know how to reproduce the
            # bug. But what I do know is that it happened, somehow.
            return False

    async def _make_mentionable(
        self, *roles: discord.Role, mod: discord.Member, mentionable: bool = True
    ):
        if not roles:
            raise ValueError("no roles were given to make mentionable")
        allowed_roles = await self.config.guild(roles[0].guild).roles()
        for role in roles:
            if role.mentionable == mentionable or role >= role.guild.me.top_role:
                continue
            # skip any roles that aren't marked as allowed to be mentioned
            if role.id not in allowed_roles:
                continue
            await role.edit(mentionable=mentionable, reason=_("Role mention by {}").format(mod))

    @staticmethod
    async def _send_message(
        content: str, author: discord.Member, channel: discord.TextChannel, *roles: discord.Role
    ):
        if not roles:
            raise ValueError
        embed = discord.Embed(colour=author.colour, description=content)
        embed.set_author(name=author.display_name, icon_url=author.avatar_url_as(format="png"))
        await channel.send(content=" ".join(x.mention for x in roles), embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def rolemention(self, ctx: commands.Context):
        """Manage role mention settings

        Role mentions can be sent by using `{{mention role: Role Name}}`

        Only users with the bot's Administrator role or with the Manage Roles permission
        may use the above mention syntax.
        """
        await cmd_help(ctx)

    async def _add_remove(self, ctx: commands.Context, role: discord.Role, *, rm: bool = False):
        if role.is_default():
            raise commands.BadArgument("cannot make a server's default role mentionable")
        async with self.config.guild(ctx.guild).roles() as roles:
            if rm is False:
                if role.id in roles:
                    await ctx.send(warning(_("That role is already mentionable")))
                    return
                roles.append(role.id)

            else:
                if role.id not in roles:
                    await ctx.send(warning(_("That role is not currently mentionable")))
                    return
                roles.remove(role.id)

            await ctx.send(
                escape(
                    tick(_("`{}` is now allowed to be mentioned").format(role.name)),
                    mass_mentions=True,
                )
                if rm is False
                else escape(
                    tick(_("`{}` is no longer allowed to be mentioned").format(role.name)),
                    mass_mentions=True,
                )
            )

    @rolemention.command(name="add")
    async def rolemention_add(self, ctx: commands.Context, *, role: discord.Role):
        """Allow a role to be mentioned"""
        await self._add_remove(ctx, role, rm=False)

    @rolemention.command(name="remove")
    async def rolemention_remove(self, ctx: commands.Context, *, role: discord.Role):
        """Disallow a role from being mentioned"""
        await self._add_remove(ctx, role, rm=True)

    @rolemention.command(name="list")
    async def rolemention_list(self, ctx: commands.Context):
        """List all roles setup to allow role mentions for"""
        roles = []
        for rid in await self.config.guild(ctx.guild).roles():
            role = discord.utils.get(ctx.guild.roles, id=rid)
            if role is None:
                continue
            roles.append(role)
        await ctx.send(
            embed=discord.Embed(
                title=_("Mentionable roles"),
                colour=discord.Colour.blurple(),
                description=" ".join([x.mention for x in roles] or [_("No mentionable roles")]),
            )
        )

    async def on_message(self, message: discord.Message):
        try:
            guild = message.guild  # type: discord.Guild
            if guild is None:
                return
        except AttributeError:
            return

        if not await self._can_mention(message):
            return

        roles = set()
        message_content = message.content
        allowed_roles = await self.config.guild(guild).roles()
        for match in self.MENTION_REGEX.finditer(message.content):
            name = match.group("NAME")
            full_match = match.group(0)
            role = discord.utils.get(guild.roles, name=name)  # type: discord.Role

            message_content = message_content.replace(
                full_match, getattr(role, "mention", full_match)
            )

            if role is None or role.id not in allowed_roles:
                continue
            roles.add(role)

        if not roles:
            return

        await self._make_mentionable(*roles, mentionable=True, mod=message.author)
        # send the parsed message with role mentions
        await self._send_message(message_content, message.author, message.channel, *roles)
        try:
            # attempt to delete the original message
            await message.delete()
        except discord.HTTPException:
            pass
        await asyncio.sleep(5)
        await self._make_mentionable(*roles, mentionable=False, mod=message.author)
