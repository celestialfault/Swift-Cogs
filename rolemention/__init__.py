from redbot.core.bot import Red
from rolemention.rolemention import RoleMention


async def setup(bot: Red):
    bot.add_cog(RoleMention(bot))
