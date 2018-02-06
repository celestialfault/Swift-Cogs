from discord.ext.commands import check


def cogs_loaded(*cogs):
    """Ensure that the cogs specified are loaded.

    Cog names are case insensitive."""
    cogs = [x.lower() for x in cogs]

    def predicate(ctx):
        bot = ctx.bot
        bot_cogs = [x.lower() for x in bot.cogs]
        return not any([x for x in cogs if x not in bot_cogs])

    return check(predicate)
