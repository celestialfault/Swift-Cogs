from discord.ext.commands import check
from redbot.core import RedContext
from redbot.core.utils.chat_formatting import warning

from .classes.starboardbase import StarboardBase

starboard = StarboardBase()


def requirerole_loaded():
    def predicate(ctx):
        return bool(ctx.bot.get_cog('RequireRole'))

    return check(predicate)


def allowed_starboard():
    async def predicate(ctx):
        if not ctx.guild:
            return True
        _starboard = starboard.starboard(ctx.guild)
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
    _starboard = starboard.starboard(ctx.guild)
    if await _starboard.channel() is None:
        await ctx.send(warning("This guild has no starboard channel setup"))
        return False
    return True
