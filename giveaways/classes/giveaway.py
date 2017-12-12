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
        # Yes - this is TECHNICALLY a dict, but it's returned with a property named json. Don't question it.
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
            winner = discord.utils.find(lambda member: member.id == winner, self.message.guild.members)
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
            self.winner = discord.utils.find(lambda member: member.id == self.winner, self.message.guild.members) \
                          or "Unknown"
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
        if self.message.pinned:
            try:
                await self.message.unpin()
            except discord.Forbidden:
                pass
        await self.save()
