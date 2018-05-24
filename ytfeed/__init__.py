from .ytfeed import YTFeed


def setup(bot):
    bot.add_cog(YTFeed(bot))
