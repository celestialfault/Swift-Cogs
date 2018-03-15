import asyncio

import re

import discord
from discord.ext import commands

from redbot.core import checks, RedContext, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import warning, escape

from odinair_libs.formatting import tick, cmd_help


class RoleMention:
    MENTION_REGEX = re.compile(r"{{mention role: ?@?(?P<NAME>[\W\w]+)}}", re.IGNORECASE)

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21312234, force_registration=True)
        self.config.register_guild(roles=[])

    async def _can_mention(self, message: discord.Message):
        try:
            guild: discord.Guild = message.guild
            if guild is None:
                return False
        except AttributeError:
            return False

        return all([
            not message.author.bot,                                   # ensure the author is not a bot account
            guild.me.guild_permissions.manage_roles,                  # make sure we have manage role permissions
            message.channel.permissions_for(guild.me).send_messages,  # and send message permissions
            any([                                                     # ensure that the author can perform this action,
                guild.me.guild_permissions.manage_roles,              # by means of having manage role permissions,
                await self.bot.is_admin(message.author),              # or by having the guild admin role
            ])
        ])

    async def _make_mentionable(self, *roles: discord.Role, by: discord.Member, mentionable: bool = True,
                                check_if_allowed: bool = True):
        if not roles:
            raise ValueError("no roles were given to make mentionable")
        allowed_roles = await self.config.guild(roles[0].guild).roles()
        for role in roles:
            if role.mentionable == mentionable or role >= role.guild.me.top_role:
                continue
            if check_if_allowed and role.id not in allowed_roles:
                continue
            await role.edit(mentionable=mentionable, reason=f"Role mention by {by!s} ({by.id})")

    @staticmethod
    async def _send_message(content: str, author: discord.Member, channel: discord.TextChannel, *roles: discord.Role):
        if not roles:
            raise ValueError
        embed = discord.Embed(colour=author.colour, description=content)
        embed.set_author(name=author.display_name, icon_url=author.avatar_url_as(format="png"))
        await channel.send(content=" ".join(x.mention for x in roles), embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def rolemention(self, ctx: RedContext):
        """Manage role mention settings

        Role mentions can be sent by using `{{mention role: Role Name}}`

        Only users with the bot's Administrator role or with the Manage Roles permission
        may use this feature.
        """
        await cmd_help(ctx, "")

    @rolemention.command(name="add")
    async def rolemention_add(self, ctx: RedContext, *, role: discord.Role):
        """Allow a role to be mentioned"""
        if role.is_default():
            await ctx.send(warning("I cannot make a guild's default role mentionable"))
            return
        async with self.config.guild(ctx.guild).roles() as roles:
            if role.id in roles:
                await ctx.send(warning("That role is already mentionable"))
                return
            roles.append(role.id)
            await ctx.send(escape(tick(f"I will now allow `{role.name}` to be mentioned"),
                                  mass_mentions=True))

    @rolemention.command(name="remove")
    async def rolemention_remove(self, ctx: RedContext, *, role: discord.Role):
        """Disallow a role from being mentioned"""
        if role.is_default():
            await ctx.send(warning("I cannot make a guild's default role mentionable"))
            return
        async with self.config.guild(ctx.guild).roles() as roles:
            if role.id not in roles:
                await ctx.send(warning("That role is not already mentionable"))
                return
            roles.remove(role.id)
            await ctx.send(escape(tick(f"I will no longer allow `{role.name}` to be mentioned"),
                                  mass_mentions=True))

    @rolemention.command(name="list")
    async def rolemention_list(self, ctx: RedContext):
        """List all roles setup to allow role mentions for"""
        roles = []
        for rid in await self.config.guild(ctx.guild).roles():
            role = discord.utils.get(ctx.guild.roles, id=rid)
            if role is None:
                continue
            roles.append(role)
        await ctx.send(embed=discord.Embed(title="Mentionable roles", colour=discord.Colour.blurple(),
                                           description=" ".join([x.mention for x in roles]
                                                                or ["No mentionable roles"])))

    @rolemention.command(name="mention")
    async def rolemention_mention(self, ctx: RedContext, role: discord.Role, *, text: str):
        """Mention a role

        This is an alternative to using the role mention syntax in a regular message.
        The role mention will be appended to the beginning of `text`
        """
        if role.id not in await self.config.guild(ctx.guild).roles():
            await ctx.send(warning("That role is not allowed to be mentioned"))
            return
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        text = f"{role.mention} {text}"
        await self._make_mentionable(role, mentionable=True, by=ctx.author)
        await self._send_message(text, ctx.author, ctx.channel, role)
        await asyncio.sleep(5)
        await self._make_mentionable(role, mentionable=False, by=ctx.author)

    async def on_message(self, message: discord.Message):
        try:
            guild: discord.Guild = message.guild
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
            role: discord.Role = discord.utils.get(guild.roles, name=name)

            message_content = message_content.replace(full_match, getattr(role, "mention", full_match))

            if role is None or role.id not in allowed_roles:
                continue
            roles.add(role)

        if not roles:
            return

        await self._make_mentionable(*roles, mentionable=True, by=message.author)
        # send the parsed message with role mentions
        await self._send_message(message_content, message.author, message.channel, *roles)
        try:
            # attempt to delete the original message
            await message.delete()
        except discord.HTTPException:
            pass
        await asyncio.sleep(5)
        await self._make_mentionable(*roles, mentionable=False, by=message.author)
