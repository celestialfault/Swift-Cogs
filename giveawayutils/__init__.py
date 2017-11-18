from redbot.core.bot import Red
from .giveaway import Giveaway


def setup(bot: Red):
    bot.add_cog(Giveaway(bot))
