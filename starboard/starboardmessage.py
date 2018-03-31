import asyncio
from datetime import datetime
from typing import Optional, List, Union

import discord

from starboard.exceptions import StarException, BlockedException, BlockedAuthorException, SelfStarException
from starboard.startype import StarType
from starboard.base import StarboardBase, get_stats
from starboard.i18n import _


__all__ = ('StarboardMessage',)


class StarboardMessage(StarboardBase):
    STARBOARD_FORMAT = "\N{WHITE MEDIUM STAR} **{stars}** {channel.mention} \N{EM DASH} ID: {message.id}"

    def __init__(self, starboard, message: discord.Message):
        from starboard.starboardguild import StarboardGuild
        if not isinstance(starboard, StarboardGuild):
            raise ValueError(f"Expected a GuildStarboard object, received {starboard.__class__.__name__}")

        self.message: discord.Message = message
        self.author: discord.Member = message.author
        self.channel: discord.TextChannel = message.channel
        self.starboard_message: discord.Message = None
        self.starrers: List[int] = []
        self.hidden = False

        self.starboard: StarboardGuild = starboard
        self.last_update = datetime.utcnow()
        self.in_queue = False
        self._save_lock = asyncio.Lock()

    def __repr__(self):
        return f"<Star stars={self.stars} hidden={self.hidden} starboard_msg={self.starboard_message!r} " \
               f"message={self.message!r} update_queued={self.in_queue}>"

    @property
    def stars(self) -> int:
        return len(self.starrers)

    @property
    def attachments(self) -> List[Union[discord.Attachment, discord.Embed]]:
        embeds: List[discord.Embed] = self.message.embeds
        image_embeds = [x for x in embeds if x.thumbnail]
        return [*self.message.attachments, *image_embeds]

    @property
    def attachment_url(self) -> Optional[str]:
        try:
            attach = self.attachments[0]
        except IndexError:
            return discord.Embed.Empty
        if isinstance(attach, discord.Attachment):
            return attach.url
        elif isinstance(attach, discord.Embed):
            return attach.thumbnail.url
        else:
            return discord.Embed.Empty

    @property
    def is_message_valid(self) -> bool:
        return self.message.content or self.attachments

    @property
    def starboard_content(self):
        return self.STARBOARD_FORMAT.format(stars=self.stars, channel=self.channel, message=self.message)

    def build_embed(self) -> Optional[discord.Embed]:
        if not self.is_message_valid:
            return None
        embed = discord.Embed(colour=discord.Colour.gold(), timestamp=self.message.created_at,
                              description=self.message.content or discord.Embed.Empty)
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url_as(format="png"))

        attach = self.attachment_url
        if attach:
            embed.set_image(url=attach)

        return embed

    def as_dict(self) -> dict:
        return {
            "channel_id": self.channel.id,
            "author_id": self.author.id,
            "members": self.starrers,
            "starboard_message": getattr(self.starboard_message, "id", None),
            "hidden": self.hidden
        }

    async def init(self, auto_create: bool = False) -> None:
        entry = await self.starboard.messages.get_raw(str(self.message.id), default=None)
        if entry is None and auto_create:
            await self._save()

        if entry is not None:
            self.starrers = entry.get("members", [])
            self.hidden = entry.get("hidden", False)

            if entry.get("starboard_message", None) is not None:
                channel = await self.starboard.starboard_channel()
                if channel is None:
                    self.starboard_message = None
                    return await self._save()

                try:
                    self.starboard_message = await channel.get_message(entry.get("starboard_message"))
                except discord.NotFound:
                    self.starboard_message = None
                    await self.queue_for_update()

    async def _save(self) -> None:
        async with self._save_lock:
            await self.starboard.messages.set_raw(str(self.message.id), value=self.as_dict())
        self.last_update = datetime.utcnow()

    async def update_cached_message(self):
        self.message = await self.channel.get_message(self.message.id)
        self.author = self.message.author
        self.channel = self.message.channel

    async def queue_for_update(self):
        if self.in_queue is True:
            return
        self.in_queue = True
        self.last_update = datetime.utcnow()
        await self.starboard.update_queue.put(self)

    async def add_star(self, member: discord.Member) -> None:
        if not self.is_message_valid:
            raise StarException()
        if member.id in self.starrers:
            raise StarException(_("The passed member already starred this message"))
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException(_("This messages author is blocked from this guild's starboard"))
        if await self.starboard.is_ignored(member):
            raise BlockedException(_("The passed member is blocked from this guild's starboard"))

        if member == self.author and not await self.starboard.selfstar():
            raise SelfStarException()

        self.starrers.append(member.id)
        await self.queue_for_update()
        await (await get_stats(member=member)).increment(StarType.GIVEN)
        await (await get_stats(member=self.author)).increment(StarType.RECEIVED)

    async def remove_star(self, member: discord.Member) -> None:
        if member.id not in self.starrers:
            raise StarException(_("The passed member hasn't starred this message"))
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException(_("This messages author is blocked from this guild's starboard"))
        if await self.starboard.is_ignored(member):
            raise BlockedException(_("The passed member is blocked from this guild's starboard"))

        self.starrers.remove(member.id)
        await self.queue_for_update()
        await (await get_stats(member=member)).decrement(StarType.GIVEN)
        await (await get_stats(member=self.author)).decrement(StarType.RECEIVED)

    def has_starred(self, member: discord.Member) -> bool:
        return member.id in self.starrers

    async def hide(self) -> bool:
        if self.hidden is True:
            return False
        self.hidden = True
        await self.queue_for_update()
        return True

    async def unhide(self) -> bool:
        if self.hidden is False:
            return False
        self.hidden = False
        await self.queue_for_update()
        return True

    async def update_starboard_message(self) -> None:
        self.in_queue = False

        min_stars = await self.starboard.min_stars()
        channel = await self.starboard.starboard_channel()
        if channel is None:
            return

        if self.stars >= min_stars and not self.hidden:
            embed = self.build_embed()
            if embed is None:
                return

            if self.starboard_message is not None:
                try:
                    await self.starboard_message.edit(content=self.starboard_content, embed=embed)
                except discord.NotFound:
                    self.starboard_message = None
                    return await self.update_starboard_message()
            else:
                try:
                    self.starboard_message = await channel.send(content=self.starboard_content, embed=embed)
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