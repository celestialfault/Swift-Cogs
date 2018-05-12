"""Shared command checks"""

from discord import Member
from discord.ext.commands import check
from redbot.core.bot import Red

__all__ = ("cogs_loaded", "bot_in_x_guilds", "bot_not_in_x_guilds", "hierarchy_allows")


def cogs_loaded(*cogs):
    """Ensure that the cogs specified are loaded.

    Cog names are case sensitive.
    """
    return check(lambda ctx: not any([x for x in cogs if x not in ctx.bot.cogs]))


def bot_in_x_guilds(guilds: int):
    """Ensure that the bot is in X guilds"""
    return check(lambda ctx: len(ctx.bot.guilds) >= guilds)


def bot_not_in_x_guilds(guilds: int):
    """Ensure that the bot is *not* in X guilds"""
    return check(lambda ctx: len(ctx.bot.guilds) < guilds)


async def hierarchy_allows(
    bot: Red, mod: Member, member: Member, *, allow_disable: bool = True
) -> bool:
    """Check if a guild's role hierarchy allows an action.

    This can be effectively disabled on a per-guild basis with the Mod cog;
    however, this can be overridden with the `allow_disable` keyword argument.
    """
    if await bot.is_owner(mod):
        return True

    guild = mod.guild
    if guild != member.guild:
        return False

    mod_cog = bot.get_cog("Mod")
    if (
        allow_disable
        and mod_cog is not None
        and not await mod_cog.settings.guild(guild).respect_hierarchy()
    ):
        return True

    # Always prevent actions taken against the guild owner
    if member == guild.owner:
        return False

    return mod.top_role > member.top_role
