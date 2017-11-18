import discord
from discord.ext import commands

from redbot.core import checks
from redbot.core.bot import Red

from random import randint


class Giveaway:
    """
    A (very hastily thrown together) giveaway utilities cog
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command(name="randomreaction", aliases=["randomreact"])
    @checks.mod_or_permissions(manage_messages=True)
    async def random_reaction(self, ctx: commands.Context, message: int, emoji: discord.Emoji=None):
        """
        Selects a random user's reaction, with an optional filter for a server emoji
        """
        try:
            message = await ctx.get_message(message)
        except discord.NotFound:
            return await ctx.send("❌ I couldn't find that message."
                                  "\n\n*(Tip: The message needs to be in the same channel this command is ran in)*")

        reactions = message.reactions
        if emoji:
            reactions = filter(lambda r: r.id == emoji.id, reactions)

        if len(reactions) == 0:
            return await ctx.send("❌ There's no reactions matching that emoji")

        users = []
        for reaction in reactions:
            u = await reaction.users().flatten()
            for user in u:
                users.append(user)

        random_user = randint(0, len(users) - 1)
        random_user = users[random_user]

        embed = discord.Embed(color=discord.Colour.blurple(),
                              title="And the winner is...",
                              description="🎉 {}! 🎉".format(random_user.mention))
        await ctx.send(embed=embed)
