from discord.ext.commands import check
from .classes.starboardbase import StarboardBase

starboard = StarboardBase()


def allowed_starboard():
    async def predicate(ctx):
        if not ctx.guild:
            return True
        _starboard = starboard.starboard(ctx.guild)
        if await _starboard.is_blocked(ctx.author):
            if await _starboard.bot.is_owner(ctx.author):
                pass
            elif await _starboard.bot.is_mod(ctx.author):
                pass
            else:
                return False
        return True

    return check(predicate)
