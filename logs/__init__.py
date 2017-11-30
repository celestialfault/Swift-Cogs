from redbot.core.bot import Red
from .logs import Logs


def setup(bot: Red):
    bot.add_cog(Logs(bot))
