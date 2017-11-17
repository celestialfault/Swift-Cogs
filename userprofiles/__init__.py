from redbot.core.bot import Red
from .userprofiles import UserProfile


def setup(bot: Red):
    bot.add_cog(UserProfile(bot))
