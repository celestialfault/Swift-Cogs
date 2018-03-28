from redbot.core.bot import Red
from rndactivity.rndactivity import RNDActivity


async def setup(bot: Red):
    bot.add_cog(RNDActivity(bot))
