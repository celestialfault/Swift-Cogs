from botmonitor.botmonitor import BotMonitor


def setup(bot):
    bot.add_cog(BotMonitor(bot))
