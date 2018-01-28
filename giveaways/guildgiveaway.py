import discord
from redbot.core.config import Config
import random


class GuildGiveaway:
    def __init__(self, message: discord.Message, creator: discord.Member, config: Config):
        self._config = config
        self.message = message
        self.creator = creator
        self.channel = message.channel
        self.winner = None
        self.entrants = None
        self.ended = False
        self.index = None
        self.description = None

    @property
    def config(self):
        return self._config.guild(self.message.guild)

    @property
    def json(self):
        return {
            "creator": self.creator.id if self.creator else "Unknown",
            "message_id": self.message.id,
            "channel_id": self.channel.id,
            "winner": self.winner.id if isinstance(self.winner, discord.Member) and self.winner is not None
            else self.winner,
            "ended": self.ended,
            "entrants": self.entrants,
            "description": self.description
        }

    def choose_winner(self):
        if not len(self.entrants):
            return None

        winner = None
        # attempt to find a winner 10 times before giving up
        attempts = 0
        while not winner and attempts < 10:
            winner = random.choice(self.entrants)
            winner = discord.utils.get(self.message.guild.members, id=winner)
            attempts += 1
        self.winner = winner

    async def setup(self, *, auto_create: bool = False, description: str=None):
        giveaways = list(await self.config.giveaways())
        entry = discord.utils.find(lambda _entry: _entry["message_id"] == self.message.id, giveaways)
        if not entry:
            if auto_create:
                await self.create(description=description)
            return
        index = giveaways.index(entry)
        self.winner = giveaways[index]["winner"]
        if self.winner is not None:
            self.winner = discord.utils.get(self.message.guild.members, id=self.winner) or "Unknown"
        self.entrants = giveaways[index]["entrants"]
        self.ended = giveaways[index]["ended"]
        self.description = giveaways[index]["description"] if "description" in giveaways[index] else "No description " \
                                                                                                     "provided"
        self.index = index

    async def create(self, description: str=None):
        from .base import GiveawayBase
        if await GiveawayBase.giveaway_message(self.message):
            raise RuntimeError("Cannot re-create entry for an already created giveaway")
        await GiveawayBase.create_entry(self.message, self.creator, description=description)
        self.description = description
        self.entrants = []
        giveaways = list(await self.config.giveaways())
        entry = discord.utils.find(lambda _entry: _entry["message_id"] == self.message.id, giveaways)
        self.index = giveaways.index(entry)

    async def update_message(self):
        ended_footer = "**Winner**: {}"
        ongoing_footer = "React with \N{PARTY POPPER} to enter!"
        desc_footer = ongoing_footer if not self.ended else ended_footer.format(self.winner.mention
                                                                                if self.winner else None)
        description = "{}\n\n{}".format(self.description, desc_footer)
        embed = discord.Embed(colour=discord.Colour.red() if self.ended else discord.Colour.blurple())
        embed.description = description
        embed.set_author(name="Giveaway #{}".format(self.index + 1), icon_url=self.creator.avatar_url)
        embed.set_footer(text="Giveaway started by {0!s}".format(self.creator))
        await self.message.edit(embed=embed)

        if self.channel.permissions_for(self.message.guild.me).manage_messages and self.ended:
            await self.message.clear_reactions()
            if self.message.pinned:
                await self.message.unpin()

    async def save(self):
        async with self.config.giveaways() as giveaways:
            if self.index is None:
                self.index = giveaways.index(discord.utils.find(lambda entry: entry["message_id"] == self.message.id,
                                                                giveaways))
            giveaways[self.index] = self.json

    async def enter(self, member: discord.Member):
        if member.bot:
            return
        if member.id in self.entrants:
            return
        self.entrants.append(member.id)
        await self.save()

    async def end(self, choose_winner: bool = True):
        if self.ended:
            raise RuntimeError("Cannot end a giveaway that already ended")
        if choose_winner:
            self.choose_winner()
        self.ended = True
        await self.save()
        if self.message:
            await self.update_message()
