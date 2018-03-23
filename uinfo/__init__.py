from redbot.core.bot import Red
from uinfo.uinfo import UInfo


async def setup(bot: Red):
    bot.add_cog(UInfo(bot))
