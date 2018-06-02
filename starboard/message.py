from datetime import datetime
from typing import List, Optional, Iterable

import discord
from discord.ext import commands
from redbot.core.commands import Context

from starboard import base
from starboard.exceptions import (
    BlockedAuthorException,
    BlockedException,
    SelfStarException,
    StarException,
)
from starboard.shared import log

__all__ = ("StarboardMessage", "AutoStarboardMessage", "resolve_starred_by")


def resolve_starred_by(data: dict):
    # boy I sure do love backwards compatibility
    return data.get("starred_by", data.get("starrers", data.get("members", [])))


class StarboardMessage(base.StarboardBase, commands.Converter):

    def __init__(self, **kwargs):
        from starboard.guild import StarboardGuild

        # these are optional for the purpose of being able to use a d.py Converter
        # instead of manually calling get_starboard().get_message() in every command
        self.message: discord.Message = kwargs.get("message")
        self.starboard: StarboardGuild = kwargs.get("starboard")

        self.starboard_message: Optional[discord.Message] = None
        self.starred_by: List[int] = []
        self.last_update = datetime.utcnow()
        self._hidden = False

    def __repr__(self):
        return (
            f"<StarboardMessage stars={self.stars} hidden={self.hidden} message={self.message!r}"
            f" update_queued={self.in_queue}>"
        )

    @property
    def as_dict(self) -> dict:
        return {
            "channel_id": self.channel.id,
            "author_id": self.author.id,
            "starred_by": self.starred_by,
            "starboard_message": getattr(self.starboard_message, "id", None),
            "hidden": self.hidden,
        }

    @classmethod
    async def convert(cls, ctx: Context, argument: str, **kwargs) -> "StarboardMessage":
        if not ctx.guild:
            raise commands.NoPrivateMessage
        from starboard.guild import StarboardGuild

        try:
            argument = int(argument)
        except ValueError:
            raise commands.BadArgument("Failed to convert the given argument to a snowflake ID")

        starboard: StarboardGuild = ctx.starboard if hasattr(
            ctx, "starboard"
        ) else base.get_starboard(ctx.guild)

        if not await starboard.resolve_starboard():
            raise commands.BadArgument("The current server has no starboard channel setup")

        message = await starboard.get_message(message_id=argument, channel=ctx.channel, **kwargs)
        if message is None:
            raise commands.BadArgument(
                "The given message ID couldn't be found - has it been starred before, "
                "or are you in the wrong channel?"
            )

        if not message.is_message_valid:
            raise commands.BadArgument(
                "The given message does not have any valid content that can be used"
            )

        if await starboard.is_ignored(message.author):
            raise commands.BadArgument("The author of that message is ignored")
        if await starboard.is_ignored(message.channel):
            raise commands.BadArgument("The channel that message is in is ignored")

        return message

    async def load_data(self, *, auto_create: bool = False) -> None:
        entry = await self.starboard.messages.get_raw(str(self.message.id), default=None)
        if entry is None and auto_create is True:
            await self._save()

        if entry is not None:
            self.starred_by = resolve_starred_by(entry)
            self._hidden = entry.get("hidden", False)

            if entry.get("starboard_message", None) is not None:
                channel = await self.starboard.resolve_starboard()
                if channel is None:
                    self.starboard_message = None
                    return await self._save()

                try:
                    self.starboard_message = await channel.get_message(
                        entry.get("starboard_message")
                    )
                except discord.NotFound:
                    self.starboard_message = None
                    self.queue_for_update()

    async def _save(self) -> None:
        log.debug(f"Saving data for message {self.message.id}")
        await self.starboard.messages.set_raw(str(self.message.id), value=self.as_dict)
        self.last_update = datetime.utcnow()

    #################################
    #   Message data

    @property
    def in_queue(self):
        return self in self.starboard.update_queue

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, hidden: bool):
        if hidden is self.hidden:
            return
        self._hidden = hidden
        self.queue_for_update()

    @property
    def author(self) -> discord.Member:
        return self.message.author

    @property
    def channel(self) -> discord.TextChannel:
        return self.message.channel

    @property
    def attachments(self) -> Iterable[str]:
        attachs = [
            *self.message.attachments,
            *[x for x in self.message.embeds if x.thumbnail or x.image],
        ]

        for attach in attachs:
            if isinstance(attach, discord.Attachment):
                yield attach.url
            elif isinstance(attach, discord.Embed):
                if attach.image:
                    yield attach.image.url
                if attach.thumbnail:
                    yield attach.thumbnail.url

    @property
    def attachment_url(self) -> Optional[str]:
        try:
            return list(self.attachments)[0]
        except IndexError:
            return discord.Embed.Empty

    @property
    def starboard_message_contents(self) -> Optional[dict]:
        if not self.is_message_valid:
            return None

        embed = discord.Embed(
            colour=discord.Colour.gold(),
            timestamp=self.message.created_at,
            description=self.message.content or discord.Embed.Empty,
        ).set_author(
            name=self.author.display_name, icon_url=self.author.avatar_url_as(format="png")
        )

        if self.attachment_url:
            embed.set_image(url=self.attachment_url)

        return {
            "content": (
                f"\N{WHITE MEDIUM STAR} **{self.stars}** {self.channel.mention} \N{EM DASH}"
                f" ID: {self.message.id}"
            ),
            "embed": embed,
        }

    @property
    def is_message_valid(self) -> bool:
        if not self.message:
            return False
        return bool(self.message.content or self.attachments)

    async def update_cached_message(self):
        self.message = await self.channel.get_message(self.message.id)

    #################################
    #   Starboard message management

    def queue_for_update(self):
        if self.in_queue:
            return
        self.last_update = datetime.utcnow()
        self.starboard.update_queue.put_nowait(self)

    async def update_starboard_message(self) -> None:
        channel = await self.starboard.resolve_starboard()
        if channel is None:
            return

        if (
            self.stars >= await self.starboard.min_stars()
            and not self.hidden
            and self.is_message_valid
        ):
            if self.starboard_message is not None:
                try:
                    await self.starboard_message.edit(**self.starboard_message_contents)
                except discord.NotFound:
                    self.starboard_message = None
                    return await self.update_starboard_message()
            else:
                try:
                    self.starboard_message = await channel.send(**self.starboard_message_contents)
                except discord.Forbidden:
                    pass
        else:
            if self.starboard_message is not None:
                try:
                    await self.starboard_message.delete()
                except (discord.HTTPException, AttributeError):
                    pass
                finally:
                    self.starboard_message = None

        await self._save()

    #################################
    #   Message stars

    @property
    def stars(self) -> int:
        return len(self.starred_by)

    def has_starred(self, member: discord.Member) -> bool:
        return member.id in self.starred_by

    async def add_star(self, member: discord.Member) -> None:
        if not self.is_message_valid or member.id in self.starred_by:
            raise StarException
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException
        if await self.starboard.is_ignored(member) or member.bot:
            raise BlockedException

        if member == self.author and not await self.starboard.selfstar():
            raise SelfStarException

        self.starred_by.append(member.id)
        self.queue_for_update()

    async def remove_star(self, member: discord.Member) -> None:
        if member.id not in self.starred_by:
            raise StarException
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException
        if await self.starboard.is_ignored(member):
            raise BlockedException

        self.starred_by.remove(member.id)
        self.queue_for_update()


class AutoStarboardMessage(StarboardMessage):
    """Alternate converter for StarboardMessage, which creates message data if it doesn't exist"""

    @classmethod
    async def convert(cls, ctx: Context, argument: str, **kwargs) -> StarboardMessage:
        return await super().convert(ctx, argument, auto_create=True)
