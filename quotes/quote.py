from datetime import datetime
from enum import Enum
from typing import List, Optional

import discord
from discord.ext import commands
from redbot.core import Config, RedContext
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n

__all__ = ("i18n", "conf", "RevisionType", "QuoteRevision", "Quote", "ensure_can_modify")

conf = Config.get_conf(
    cog_instance=None, cog_name="Quotes", identifier=441356724, force_registration=True
)
conf.register_guild(quotes=[])

i18n = CogI18n("Quotes", __file__)


async def ensure_can_modify(member: discord.Member, quote: "Quote"):
    # https://u.odinair.xyz/bBQzxMd.png
    # > 'about one hour to fix'
    # it took me longer to upload that screenshot than to actually fix this
    if not await quote.can_modify(member):
        raise commands.CheckFailure


class RevisionType(Enum):
    CONTENT = i18n("Content")
    ATTRIBUTED_AUTHOR = i18n("Attributed Author")
    QUOTE_CREATOR = i18n("Quote Creator")


class QuoteRevision:

    def __init__(
        self,
        quote: "Quote",
        rev_type: RevisionType,
        changed_from,
        changed_to,
        rev_id: int,
        timestamp: datetime = None,
    ):
        self.quote = quote
        self.type = rev_type
        self.changed_from = changed_from
        self.changed_to = changed_to
        self.id = rev_id
        self.timestamp = timestamp or datetime.utcnow()

    def __int__(self):
        return self.id

    @property
    def title(self):
        return i18n("Revision #{}").format(self.id)

    def summary(self, prefix: str = "[p]"):
        return i18n(
            "**Type:** {type} \N{LIGHT VERTICAL BAR} Use `{prefix}quote history {quote} {rev}` "
            "to view this revision"
        ).format(
            type=self.type.value, prefix=prefix, quote=self.quote.id, rev=self.id
        )

    def embed(self, colour: discord.Colour = discord.Colour.blurple()):
        changed_from = self.changed_from
        changed_to = self.changed_to
        if isinstance(changed_from, discord.Member):
            changed_from = changed_from.mention
        if isinstance(changed_to, discord.Member):
            changed_to = changed_to.mention

        return (
            discord.Embed(colour=colour, title=self.title, timestamp=self.timestamp).add_field(
                name=i18n("Before"), value=changed_from, inline=False
            ).add_field(
                name=i18n("After"), value=changed_to, inline=False
            )
        )

    @classmethod
    def from_dict(cls, quote: "Quote", rev_id: int, data: dict):
        ts = datetime.fromtimestamp(data.get("timestamp"))
        rev_type = getattr(RevisionType, data.get("rev_type"))
        if rev_type in (RevisionType.ATTRIBUTED_AUTHOR, RevisionType.QUOTE_CREATOR):
            changed_from = quote.guild.get_member(data.get("changed_from")) or data.get(
                "changed_from"
            )
            changed_to = quote.guild.get_member(data.get("changed_to")) or data.get("changed_to")
        else:
            changed_from = data.get("changed_from")
            changed_to = data.get("changed_to")
        return cls(quote, rev_type, changed_from, changed_to, rev_id, ts)

    @property
    def as_dict(self):
        return {
            "rev_type": self.type.name,
            "changed_from": self.changed_from.id
            if isinstance(self.changed_from, discord.Member)
            else self.changed_from,
            "changed_to": self.changed_to.id
            if isinstance(self.changed_to, discord.Member)
            else self.changed_to,
            "timestamp": self.timestamp.timestamp(),
        }


class Quote(commands.Converter):
    bot = None  # type: Red

    def __init__(self, **kwargs):
        self.guild = kwargs.get("guild")  # type: discord.Guild
        self.id = kwargs.get("id")  # type: id
        self._text = kwargs.get("text")  # type: str
        self._message_author = kwargs.get("message_author_id")  # type: int
        self._creator = kwargs.get("author_id")  # type: int
        self.timestamp = datetime.fromtimestamp(
            kwargs.get("timestamp", datetime.utcnow().timestamp())
        )  # type: datetime

        revisions = kwargs.get("revisions", [])
        self.revisions = [
            QuoteRevision.from_dict(self, data=x, rev_id=revisions.index(x) + 1) for x in revisions
        ]

    def __int__(self):
        return self.id

    def __str__(self):
        return self.text

    def _add_rev(self, rev_type: RevisionType, old, new):
        self.revisions.append(QuoteRevision(self, rev_type, old, new, len(self.revisions)))

    @property
    def embed_user(self):
        return self.message_author or self.creator

    @property
    def embed_colour(self):
        colour = getattr(self.embed_user, "colour", discord.Color.blurple())
        colour = colour if colour != discord.Colour.default() else discord.Colour.blurple()
        return colour

    @property
    def icon_uri(self):
        if self.embed_user:
            return self.embed_user.avatar_url_as(format="png")
        else:
            return self.guild.icon_url

    @property
    def text(self):
        """Get the quote text"""
        return self._text

    @text.setter
    def text(self, text: str):
        """Set the quote text. This creates a revision history entry"""
        if text == self.text:
            return
        self._add_rev(RevisionType.CONTENT, self.text, text)
        self._text = text

    @property
    def creator(self) -> Optional[discord.Member]:
        """Get the user who created the current quote"""
        return self.guild.get_member(self._creator)

    @creator.setter
    def creator(self, creator: discord.Member):
        """Change the user who created the quote. This creates a revision history entry"""
        if creator == self.creator:
            return
        self._add_rev(RevisionType.QUOTE_CREATOR, self.creator, creator)
        self._creator = creator.id

    @property
    def message_author(self) -> Optional[discord.Member]:
        """Get the author of the quoted message"""
        return self.guild.get_member(self._message_author)

    @message_author.setter
    def message_author(self, message_author: discord.Member):
        """Set the quoted message author. This creates a revision history entry"""
        if message_author == self.message_author:
            return
        self._add_rev(RevisionType.ATTRIBUTED_AUTHOR, self.message_author, message_author)
        self._message_author = message_author.id

    @property
    def embed(self):
        """Get a prepared embed for the current quote"""
        embed = discord.Embed(
            colour=self.embed_colour, description=self.text, timestamp=self.timestamp
        ).set_author(
            name=getattr(self.embed_user, "name", i18n("Unknown quote author")),
            icon_url=self.icon_uri,
        )

        if self.creator:
            embed.set_footer(text=i18n("Quote #{} | Quoted by {!s}").format(self.id, self.creator))
        else:
            embed.set_footer(text=i18n("Quote #{} | Quoted by an unknown user").format(self.id))

        return embed

    @property
    def as_dict(self) -> dict:
        """Get the current quote's raw data"""
        return {
            "author_id": getattr(self.creator, "id", self.creator),
            "message_author_id": getattr(self.message_author, "id", self.message_author),
            "text": self.text,
            "timestamp": self.timestamp.timestamp(),
            "revisions": [x.as_dict for x in self.revisions],
        }

    async def can_modify(self, member: discord.Member) -> bool:
        """Check if the given member can modify the current quote"""
        return any(
            [
                getattr(self.message_author, "id", None) == member.id,
                getattr(self.creator, "id", None) == member.id,
                await self.bot.is_mod(member),
                await self.bot.is_owner(member),
            ]
        )

    async def save(self):
        """Save any changes made to the current quote"""
        async with conf.guild(self.guild).quotes() as quotes:
            quotes[self.id - 1].update(self.as_dict)

    async def delete(self):
        """Delete the current quote"""
        async with conf.guild(self.guild).quotes() as quotes:
            del quotes[self.id - 1]

    @classmethod
    async def get(cls, guild: discord.Guild, quote_id: int) -> Optional["Quote"]:
        """Retrieve a specific quote from a guild"""
        quotes = list(await conf.guild(guild).quotes())
        if 0 < len(quotes) >= quote_id:
            return cls(guild=guild, id=quote_id, **quotes[quote_id - 1])
        return None

    @classmethod
    async def create(
        cls, text: str, author: discord.Member, message_author: discord.Member = None
    ) -> Optional["Quote"]:
        guild = author.guild
        quote = {
            "author_id": author.id,
            "message_author_id": getattr(message_author, "id", author.id),
            "text": text,
            "timestamp": datetime.utcnow().timestamp(),
            "revisions": [],
        }
        async with conf.guild(guild).quotes() as quotes:
            quotes.append(quote)
        return cls(guild=guild, **quote, id=len(quotes))

    @classmethod
    async def all_quotes(cls, guild: discord.Guild) -> List["Quote"]:
        quotes = []
        for i in range(len(await conf.guild(guild).quotes())):
            quotes.append(await cls.get(guild, quote_id=i + 1))
        return quotes

    # noinspection PyMethodOverriding
    @staticmethod
    async def convert(ctx: RedContext, argument: str):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        try:
            quote_id = int(argument)
        except ValueError:
            raise commands.BadArgument

        quote = await Quote.get(ctx.guild, quote_id)
        if not quote:
            raise commands.BadArgument
        return quote
