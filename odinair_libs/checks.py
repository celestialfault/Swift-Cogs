from discord.ext.commands import check


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
