from redbot.core.bot import Red
from starboard.starboard import Starboard


def setup(bot: Red):
    bot.add_cog(Starboard(bot))
