from redbot.core.bot import Red
from .cogwhitelist import CogWhitelist


def setup(bot: Red):
    bot.add_cog(CogWhitelist(bot))
