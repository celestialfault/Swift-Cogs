from redbot.core.bot import Red
from .quotes import Quotes


def setup(bot: Red):
    bot.add_cog(Quotes(bot))
