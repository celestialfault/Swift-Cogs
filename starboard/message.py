from datetime import datetime
from typing import List, Optional, Union

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
from starboard.log import log

__all__ = ("StarboardMessage", "AutoStarboardMessage")


class StarboardMessage(base.StarboardBase, commands.Converter):
    STARBOARD_FORMAT = "\N{WHITE MEDIUM STAR} **{stars}** {channel} \N{EM DASH} ID: {id}"

    def __init__(self, **kwargs):
        from starboard.guild import StarboardGuild

        self.message = kwargs.get("message", None)  # type: discord.Message
        self.starboard_message = None  # type: discord.Message
        self.starrers: List[int] = []

        self.starboard: StarboardGuild = kwargs.get("starboard", None)
        self.last_update = datetime.utcnow()
        self._hidden = False

    def __repr__(self):
        return (
            "<StarboardMessage stars={self.stars} hidden={self.hidden} message={self.message!r}"
            " update_queued={self.in_queue}>".format(self=self)
        )

    @staticmethod
    async def _convert(ctx: Context, argument: str, **kwargs):
        from starboard.guild import StarboardGuild

        try:
            argument = int(argument)
        except ValueError:
            raise commands.BadArgument("Failed to convert the given argument to a snowflake ID")

        starboard = base.get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=argument, channel=ctx.channel, **kwargs)
        if message is None:
            raise commands.BadArgument(
                "The given message ID couldn't be found - has it been starred before, "
                "or are you in the wrong channel?"
            )

        return message

    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        return await cls._convert(ctx, argument)

    async def load_data(self, *, auto_create: bool = False) -> None:
        entry = await self.starboard.messages.get_raw(str(self.message.id), default=None)
        if entry is None and auto_create is True:
            await self._save()

        if entry is not None:
            self.starrers = entry.get("starrers", entry.get("members", []))
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
        log.debug("Saving data for message {}".format(self.message.id))
        await self.starboard.messages.set_raw(
            str(self.message.id),
            value={
                "channel_id": self.channel.id,
                "author_id": self.author.id,
                "starrers": self.starrers,
                "starboard_message": getattr(self.starboard_message, "id", None),
                "hidden": self.hidden,
            },
        )
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
    def attachments(self) -> List[Union[discord.Attachment, discord.Embed]]:
        embeds = self.message.embeds  # type: List[discord.Embed]
        image_embeds = [x for x in embeds if x.thumbnail or x.image]
        return [*self.message.attachments, *image_embeds]

    @property
    def attachment_url(self) -> Optional[str]:
        try:
            attach = self.attachments[0]
        except IndexError:
            return discord.Embed.Empty
        else:
            if isinstance(attach, discord.Attachment):
                return attach.url
            elif isinstance(attach, discord.Embed):
                if attach.image:
                    return attach.image.url
                elif attach.thumbnail:
                    return attach.thumbnail.url
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
            "content": self.STARBOARD_FORMAT.format(
                stars=self.stars, channel=self.channel.mention, id=self.message.id
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
        return len(self.starrers)

    def has_starred(self, member: discord.Member) -> bool:
        return member.id in self.starrers

    async def add_star(self, member: discord.Member) -> None:
        if not self.is_message_valid or member.id in self.starrers:
            raise StarException
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException
        if await self.starboard.is_ignored(member) or member.bot:
            raise BlockedException

        if member == self.author and not self.starboard.selfstar:
            raise SelfStarException()

        self.starrers.append(member.id)
        self.queue_for_update()

    async def remove_star(self, member: discord.Member) -> None:
        if member.id not in self.starrers:
            raise StarException
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException
        if await self.starboard.is_ignored(member):
            raise BlockedException

        self.starrers.remove(member.id)
        self.queue_for_update()


class AutoStarboardMessage(StarboardMessage):
    """Alternate converter for StarboardMessage, which creates message data if it doesn't exist"""

    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        return await cls._convert(ctx, argument, auto_create=True)
