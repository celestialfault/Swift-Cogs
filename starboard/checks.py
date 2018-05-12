from discord.ext.commands import check
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import warning

from starboard import base
from starboard.i18n import i18n


def can_use_starboard():

    async def predicate(ctx):
        if not ctx.guild:
            return True
        _starboard = base.get_starboard(ctx.guild)
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


async def guild_has_starboard(ctx: Context):
    _starboard = base.get_starboard(ctx.guild)
    if await _starboard.get_channel() is None:
        await ctx.send(warning(i18n("This server has no starboard channel setup")))
        return False
    return True
