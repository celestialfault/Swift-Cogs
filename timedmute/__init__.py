from redbot.core.bot import Red
from timedmute.timedmute import TimedMute


async def setup(bot: Red):
    bot.add_cog(TimedMute(bot))
