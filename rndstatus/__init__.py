from redbot.core.bot import Red
from .rndstatus import RNDStatus


def setup(bot: Red):
    bot.add_cog(RNDStatus(bot))
