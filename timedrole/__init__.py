from .timedrole import TimedRole


def setup(bot):
    bot.add_cog(TimedRole(bot))
