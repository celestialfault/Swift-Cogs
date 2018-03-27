from discord import Member
from discord.ext.commands import check

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import warning

from starboard import base
from starboard.i18n import _


def can_migrate():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        _starboard = await base.get_starboard(ctx.guild)
        return await _starboard.migrate(dry_run=True) > 0

    return check(predicate)


def can_use_starboard():
    async def predicate(ctx):
        if not ctx.guild:
            return True
        _starboard = await base.get_starboard(ctx.guild)
        if await _starboard.is_ignored(ctx.channel):
            return False
        if await _starboard.is_ignored(ctx.author):
            if await _starboard.bot.is_owner(ctx.author):
                pass
            elif await _starboard.bot.is_mod(ctx.author):
                pass
            else:
                return False
        return True

    return check(predicate)


async def guild_has_starboard(ctx: RedContext):
    _starboard = await base.get_starboard(ctx.guild)
    if await _starboard.starboard_channel() is None:
        await ctx.send(warning(_("This guild has no starboard channel setup")))
        return False
    return True


async def hierarchy_allows(bot: Red, mod: Member, member: Member) -> bool:
    if await bot.is_owner(mod):
        return True
    guild = mod.guild
    if guild != member.guild:
        return False
    return any([
        guild.owner == mod,  # guild owner
        # guild admin and member is not an admin
        await bot.is_admin(mod) and not (await bot.is_admin(member) or guild.owner == member),
        # guild mod and member is not a mod
        await bot.is_mod(mod) and not (await bot.is_mod(member) or guild.owner == member)
    ])
