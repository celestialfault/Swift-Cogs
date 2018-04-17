from datetime import datetime
from enum import Enum
from typing import Optional, List

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n

__all__ = ('i18n', 'conf', 'RevisionType', 'QuoteRevision', 'Quote')

conf = Config.get_conf(cog_instance=None, cog_name="Quotes", identifier=441356724, force_registration=True)
conf.register_guild(quotes=[])

i18n = CogI18n("Quotes", __file__)


class RevisionType(Enum):
    CONTENT = i18n("Content")
    ATTRIBUTED_AUTHOR = i18n("Attributed Author")
    QUOTE_CREATOR = i18n("Quote Creator")


class QuoteRevision:
    def __init__(self, quote: "Quote", rev_type: RevisionType, changed_from, changed_to, rev_id: int,
                 timestamp: datetime = None):
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
            "**Type:** {type} \N{LIGHT VERTICAL BAR} Use `{prefix}quote history {quote} {rev}` to view this revision"
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
            discord.Embed(colour=colour, title=self.title, timestamp=self.timestamp)
            .add_field(name=i18n("Before"), value=changed_from, inline=False)
            .add_field(name=i18n("After"), value=changed_to, inline=False)
        )

    @classmethod
    def from_dict(cls, quote: "Quote", rev_id: int, data: dict):
        ts = datetime.fromtimestamp(data.get("timestamp"))
        rev_type = getattr(RevisionType, data.get("rev_type"))
        if rev_type in (RevisionType.ATTRIBUTED_AUTHOR, RevisionType.QUOTE_CREATOR):
            changed_from = quote.guild.get_member(data.get("changed_from")) or data.get("changed_from")
            changed_to = quote.guild.get_member(data.get("changed_to")) or data.get("changed_to")
        else:
            changed_from = data.get("changed_from")
            changed_to = data.get("changed_to")
        return cls(quote, rev_type, changed_from, changed_to, rev_id, ts)

    @property
    def as_dict(self):
        return {
            'rev_type': self.type.name,
            'changed_from': self.changed_from.id if isinstance(self.changed_from,
                                                               discord.Member) else self.changed_from,
            'changed_to': self.changed_to.id if isinstance(self.changed_to, discord.Member) else self.changed_to,
            'timestamp': self.timestamp.timestamp()
        }


class Quote:
    bot = None  # type: Red

    def __init__(self, guild: discord.Guild, **kwargs):
        self.guild = guild
        self.id = kwargs.get("id")  # type: id
        self._text = kwargs.get("text")  # type: str
        self._message_author = kwargs.get("message_author_id")  # type: int
        self._creator = kwargs.get("author_id")  # type: int
        self.timestamp = datetime.fromtimestamp(kwargs.get("timestamp", datetime.utcnow().timestamp())
                                                )  # type: datetime

        revisions = kwargs.get("revisions", [])
        self.revisions = [QuoteRevision.from_dict(self, data=x, rev_id=revisions.index(x) + 1) for x in revisions]

    def __int__(self):
        return self.id

    def __str__(self):
        return self.text

    def _add_rev(self, rev_type: RevisionType, old, new):
        self.revisions.append(QuoteRevision(self, rev_type, old, new, len(self.revisions)))

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        if text == self.text:
            return
        self._add_rev(RevisionType.CONTENT, self.text, text)
        self._text = text

    @property
    def creator(self) -> Optional[discord.Member]:
        return self.guild.get_member(self._creator)

    @creator.setter
    def creator(self, creator: discord.Member):
        if creator == self.creator:
            return
        self._add_rev(RevisionType.QUOTE_CREATOR, self.creator, creator)
        self._creator = creator.id

    @property
    def message_author(self) -> Optional[discord.Member]:
        return self.guild.get_member(self._message_author)

    @message_author.setter
    def message_author(self, message_author: discord.Member):
        if message_author == self.message_author:
            return
        self._add_rev(RevisionType.ATTRIBUTED_AUTHOR, self.message_author, message_author)
        self._message_author = message_author.id

    @property
    def embed(self):
        colour = discord.Colour.blurple()
        if self.message_author and self.message_author.colour != discord.Colour.default():
            colour = self.message_author.colour
        elif self.creator and self.creator.colour != discord.Colour.default():
            colour = self.creator.colour

        embed = discord.Embed(colour=colour, description=self.text, timestamp=self.timestamp)

        if self.message_author:  # Check if we found the message author
            embed.set_author(name=self.message_author.display_name, icon_url=self.message_author.avatar_url_as(
                format="png"))
        elif self.creator:  # Attempt to fall back to the quote creator
            embed.set_author(name=self.creator.display_name, icon_url=self.creator.avatar_url_as(format="png"))
        else:
            embed.set_author(name=i18n("Unknown quote author"), icon_url=self.guild.icon_url)

        footer_str = i18n("Quote #{}").format(self.id)
        if self.creator != self.message_author:
            footer_str = i18n("Quote #{} | Quoted by {}").format(self.id, str(self.creator))
        embed.set_footer(text=footer_str)

        return embed

    @property
    def as_dict(self) -> dict:
        return {
            'author_id': getattr(self.creator, "id", self.creator),
            'message_author_id': getattr(self.message_author, "id", self.message_author),
            'text': self.text,
            'timestamp': self.timestamp.timestamp(),
            'revisions': [x.as_dict for x in self.revisions]
        }

    async def can_modify(self, member: discord.Member) -> bool:
        return any([getattr(self.message_author, "id", None) == member.id,
                    getattr(self.creator, "id", None) == member.id,
                    await self.bot.is_mod(member), await self.bot.is_owner(member)])

    async def save(self):
        async with conf.guild(self.guild).quotes() as quotes:
            quotes[self.id - 1].update(self.as_dict)

    async def delete(self):
        async with conf.guild(self.guild).quotes() as quotes:
            del quotes[self.id - 1]

    @classmethod
    async def get(cls, guild: discord.Guild, quote_id: int) -> Optional["Quote"]:
        quotes = list(await conf.guild(guild).quotes())
        if 0 < len(quotes) >= quote_id:
            return cls(guild, **quotes[quote_id - 1], id=quote_id)
        return None

    @classmethod
    async def create(cls, text: str, author: discord.Member,
                     message_author: discord.Member = None) -> Optional["Quote"]:
        guild = author.guild
        quote = {
            'author_id': author.id,
            'message_author_id': getattr(message_author, "id", author.id),
            'text': text,
            'timestamp': datetime.utcnow().timestamp(),
            'revisions': []
        }
        async with conf.guild(guild).quotes() as quotes:
            quotes.append(quote)
        return cls(guild, **quote, id=len(quotes))

    @classmethod
    async def all_quotes(cls, guild: discord.Guild) -> List["Quote"]:
        quotes = []
        for i in range(len(await conf.guild(guild).quotes())):
            quotes.append(await cls.get(guild, quote_id=i + 1))
        return quotes
