from discord import Member
from discord.ext.commands import check
from redbot.core.bot import Red


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
