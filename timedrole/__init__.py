from redbot.core.bot import Red
from timedrole.timedrole import TimedRole


async def setup(bot: Red):
    bot.add_cog(TimedRole(bot))
