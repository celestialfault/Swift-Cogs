from redbot.core.bot import Red
from requirerole.requirerole import RequireRole


def setup(bot: Red):
    bot.add_cog(RequireRole(bot))
