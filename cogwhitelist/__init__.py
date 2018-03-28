from redbot.core.bot import Red
from cogwhitelist.cogwhitelist import CogWhitelist


def setup(bot: Red):
    bot.add_cog(CogWhitelist(bot))
