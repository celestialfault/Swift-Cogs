from redbot.core.bot import Red
from misctools.misctools import MiscTools


async def setup(bot: Red):
    bot.add_cog(MiscTools(bot))
