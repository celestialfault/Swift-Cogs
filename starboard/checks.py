from redbot.core import commands

from starboard import base


def can_use_starboard():

    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        # mfw checks are run before __before_invoke hooks
        starboard = base.get_starboard(ctx.guild)

        if await starboard.resolve_starboard() is None:
            raise commands.CheckFailure("The current server has no starboard channel setup")

        if await starboard.is_ignored(ctx.author) and not (
            await starboard.bot.is_owner(ctx.author) or await starboard.bot.is_mod(ctx.author)
        ):
            raise commands.CheckFailure("Command issuer is ignored from this server's starboard")
        return True

    return commands.check(predicate)
