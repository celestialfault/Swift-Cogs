import discord
from discord.ext import commands

from redbot.core.bot import Red
from redbot.core import Config, RedContext, checks

from typing import Union

from redbot.core.utils.chat_formatting import error, info, bold

from .classes.base import GiveawayBase


class Giveaway(GiveawayBase):
    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config

    @commands.group(name="giveaway", aliases=["giveaways"])
    async def _giveaway(self, ctx: RedContext):
        """Manage giveaways"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_giveaway.command(name="new", aliases=["start"])
    async def _giveaway_new(self, ctx: RedContext, *, description: str):
        """Create a new giveaway"""
        if await self.guild_config(ctx.guild).mod_only() and\
                not await self.bot.is_mod(ctx.author) and not await self.bot.is_owner(ctx.author):
            await ctx.send(error("You aren't authorized to create giveaways in this guild"))
            return
        __len = len(await self.get_giveaways(ctx.guild, ctx.channel))
        if __len >= 50:
            await ctx.send(error("Failed to create giveaway - there's 50 currently ongoing giveaways in this channel"))
            return
        description = description[:750]
        _description = "{}\n\nReact with \N{PARTY POPPER} to enter!".format(description)
        embed = discord.Embed(colour=discord.Colour.blurple(), description=_description)
        embed.set_author(name="Giveaway #{}".format(len(await self.get_giveaways(ctx.guild)) + 1),
                         icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Giveaway started by {}".format(str(ctx.author)))
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\N{PARTY POPPER}")
        # create the giveaway
        await self.giveaway_message(msg, creator=ctx.author, auto_create=True, description=description)
        if await self.guild_config(ctx.guild).pin_messages():
            try:
                await msg.pin()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        try:
            # try to delete the command message
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    @_giveaway.command(name="list")
    async def _giveaway_list(self, ctx: RedContext, page: int=1, guild: bool=False):
        """Lists all currently ongoing giveaways in this channel, or the entire guild if guild is passed"""
        per_page = 20
        page = page - 1
        skip = page * per_page
        skipped = 0
        msg = ""
        channels = {}
        guild_giveaways = list(await self.guild_config(ctx.guild).giveaways())
        if guild:
            for item in guild_giveaways:
                if item["ended"]:
                    continue
                if skipped < skip:
                    skipped += 1
                    continue
                if item["channel_id"] not in channels:
                    channels[item["channel_id"]] = []
                channels[item["channel_id"]].append(item)
        else:
            channels[ctx.channel.id] = list(await self.get_giveaways(ctx.guild, ctx.channel))[skip:skip+per_page]
        for channel in channels:
            msg += "\n\n**❯** Channel {}:\n\n".format(self.bot.get_channel(channel).mention)
            msg += ", ".join([bold("#" + str(guild_giveaways.index(x) + 1)) for x in channels[channel]]
                             or ["No ongoing giveaways"])
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.description = msg.rstrip()
        embed.set_author(name="Ongoing Giveaways", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @_giveaway.command(name="info", aliases=["show"])
    async def _giveaway_info(self, ctx: RedContext, giveaway: int):
        giveaways = await self.get_giveaways(ctx.guild)
        if len(giveaways) < giveaway:
            await ctx.send(error("That giveaway doesn't exist"))
            return
        giveaway = giveaways[giveaway - 1]
        giveaway = await self.giveaway_message(
            await self.bot.get_channel(giveaway["channel_id"]).get_message(giveaway["message_id"]))
        embed = discord.Embed(colour=discord.Colour.blurple() if not giveaway.ended else discord.Colour.red())
        giveaways = await self.guild_config(ctx.guild).giveaways()
        giveaway_entry = discord.utils.find(lambda entry: entry["message_id"] == giveaway.message.id, giveaways)
        index = giveaways.index(giveaway_entry)
        embed.set_author(name="Giveaway #{}".format(index + 1),
                         icon_url=ctx.author.avatar_url)
        embed.add_field(name="Winner", value=str(giveaway.winner) if giveaway.ended else "Giveaway is ongoing")
        embed.add_field(name="Creator", value=str(giveaway.creator))
        embed.add_field(name="Entered Users", value=str(len(giveaway.entrants)))
        embed.add_field(name="Description", value=giveaway.description or "No description provided", inline=False)
        await ctx.send(embed=embed)

    @_giveaway.command(name="end")
    async def _giveaway_end(self, ctx: RedContext, giveaway: int, choose_winner: bool=True):
        """End a currently running giveaway"""
        giveaways = await self.get_giveaways(ctx.guild)
        if len(giveaways) < giveaway:
            await ctx.send(error("That giveaway doesn't exist"))
            return
        giveaway = giveaways[giveaway - 1]
        giveaway = await self.giveaway_message(
            await self.bot.get_channel(giveaway["channel_id"]).get_message(giveaway["message_id"]))
        if giveaway.ended:
            await ctx.send(error("That giveaway has already ended"))
            return
        if giveaway.creator:
            if isinstance(giveaway.creator, discord.Member):
                creator = giveaway.creator.id
            else:
                creator = giveaway.creator
            if ctx.author.id != creator:
                if await self.bot.is_owner(ctx.author):
                    pass
                elif await self.bot.is_mod(ctx.author):
                    pass
                else:
                    await ctx.send(error("You aren't allowed to end that giveaway"))
                    return
        await giveaway.end(choose_winner=choose_winner)
        winner = giveaway.winner
        if winner:
            description = "\N{PARTY POPPER} {} has won the giveaway! \N{PARTY POPPER}".format(winner.mention)
        else:
            description = "No one won the giveaway."
        embed = discord.Embed(colour=discord.Colour.blurple(), description=description)
        giveaways = await self.guild_config(ctx.guild).giveaways()
        giveaway_entry = discord.utils.find(lambda entry: entry["message_id"] == giveaway.message.id, giveaways)
        index = giveaways.index(giveaway_entry)
        embed.set_author(name="Giveaway #{}".format(index + 1),
                         icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @_giveaway.command(name="pin")
    @checks.admin_or_permissions(manage_messages=True)
    async def _giveaway_pin(self, ctx: RedContext):
        """Toggle whether or not giveaway messages are automatically pinned

        This is useful if anyone can create giveaways in your guild"""
        status = await self.guild_config(ctx.guild).pin_messages()
        toggle = not status
        await self.guild_config(ctx.guild).pin_messages.set(toggle)
        await ctx.send(info("Giveaway messages will {}".format("now be pinned" if toggle else "no longer be pinned")))

    @_giveaway.command(name="modonly", aliases=["mods"])
    @checks.admin_or_permissions(administrator=True)
    async def _giveaway_modonly(self, ctx: RedContext):
        """Toggle if only moderators can create giveaways in the current guild"""
        status = await self.guild_config(ctx.guild).mod_only()
        toggle = not status
        await self.guild_config(ctx.guild).mod_only.set(toggle)
        await ctx.send(info("Giveaways can now be created by {}".format("only moderators" if toggle
                                                                        else "anyone")))

    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if user.bot:
            return
        if not isinstance(user, discord.Member):
            return
        if str(reaction.emoji) != "\N{PARTY POPPER}":
            return
        message = reaction.message
        if message.author.id != reaction.message.guild.me.id:
            return
        msg = await self.giveaway_message(message)
        if not msg:
            return
        if not msg.ended:
            await msg.enter(user)
