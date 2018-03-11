from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import discord

from .exceptions import *
from .starboardbase import StarboardBase


class Star(StarboardBase):
    """Starboard message"""

    STARBOARD_FORMAT = "\N{WHITE MEDIUM STAR} **{stars}** {channel.mention} \N{EM DASH} ID: {message.id}"

    def __init__(self, starboard, message: discord.Message):
        from .guildstarboard import GuildStarboard
        if not isinstance(starboard, GuildStarboard):
            raise ValueError(f"Expected a GuildStarboard object, received {starboard.__class__.__name__}")

        self.starboard: GuildStarboard = starboard
        self.message: discord.Message = message
        self.author: discord.Member = message.author
        self.channel: discord.TextChannel = message.channel
        self.starboard_message: discord.Message = None
        self.starrers = []
        self.hidden = False

        # Do not modify these values directly
        self._entry: Dict[str, Any] = None
        self.in_queue = False
        self.last_update = datetime.utcnow()

    def __repr__(self):
        return "<Star stars={0} hidden={1} starboard_msg={2!r} message={3!r} update_queued={4}>".format(
            self.stars,
            self.hidden,
            self.starboard_message,
            self.message,
            self.in_queue
        )

    @property
    def stars(self) -> int:
        """Returns the amount of members who have starred this message"""
        return len(self.starrers)

    @property
    def exists(self) -> bool:
        return self._entry is not None

    @property
    def attachments(self) -> List[Union[discord.Attachment, discord.Embed]]:
        embeds: List[discord.Embed] = self.message.embeds
        image_embeds = [x for x in embeds if x.thumbnail]
        return [*self.message.attachments, *image_embeds]

    @property
    def attachment_url(self):
        try:
            attach = self.attachments[0]
        except IndexError:
            return discord.Embed.Empty
        if isinstance(attach, discord.Attachment):
            return attach.url
        elif isinstance(attach, discord.Embed):
            return attach.thumbnail.url

    @property
    def is_message_valid(self) -> bool:
        return self.message.content or self.attachments

    async def queue_for_update(self):
        if self.in_queue is True:
            return
        self.in_queue = True
        self.last_update = datetime.utcnow()
        await self.starboard.queue.put(self)

    def build_embed(self) -> Optional[discord.Embed]:
        if not self.is_message_valid:
            return None
        embed = discord.Embed(colour=discord.Colour.gold(), timestamp=self.message.created_at,
                              description=self.message.content or discord.Embed.Empty)
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url_as(format="png"))
        embed.set_image(url=self.attachment_url)
        return embed

    async def init(self, auto_create: bool = False) -> None:
        if self._entry is not None:
            raise RuntimeError("Cannot re-instantiate an already created Star object")
        self._entry = await self.starboard.messages.get_raw(str(self.message.id), default=None)
        if self._entry is None and auto_create:
            await self._create()

        if self._entry is not None:
            self.starrers = self._entry.get("members", [])
            self.hidden = self._entry.get("hidden", False)

            if self._entry.get("starboard_message", None) is not None:
                channel = await self.starboard.channel()
                if channel is None:
                    self.starboard_message = None
                    return await self.save()

                try:
                    self.starboard_message = await channel.get_message(self._entry.get("starboard_message", None))
                except discord.NotFound:
                    self.starboard_message = None
                    await self.queue_for_update()

    async def save(self) -> None:
        """Updates the star's guild starboard entry"""
        if not self._entry:
            return
        self._entry.update({
            "members": self.starrers,
            "starboard_message": getattr(self.starboard_message, "id", None),
            "hidden": self.hidden,
            "author_id": self.author.id
        })
        await self.starboard.messages.get_attr(str(self.message.id)).set(self._entry)

    async def _create(self) -> None:
        """Creates the message's starboard entry

        This is useful if you didn't pass auto_create when creating the Star object
        """
        if self._entry is not None:
            raise StarboardException("This message already has an entry")
        self._entry = {
            "channel_id": self.channel.id,
            "author_id": self.author.id,
            "members": [],
            "starboard_message": None,
            "hidden": False
        }
        await self.save()
        self.last_update = datetime.utcnow()

    async def add_star(self, member: discord.Member) -> None:
        """Adds a member's star

        Parameters
        -----------
        member: discord.Member
            The member to add the star for

        Raises
        -------
        StarException
            Raised if the member given has already starred this message
        BlockedException
            Raised if the member given is blocked from using this guild's starboard
        BlockedAuthorException
            Raised if the author of this message is blocked from using this guild's starboard
        NoMessageContent
            Raised if the message cannot be starred due to a lack of content or attachments
        """
        if not self.is_message_valid:
            raise NoMessageContent()
        if member.id in self.starrers:
            raise StarException("The passed member already starred this message")
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException()
        if await self.starboard.is_ignored(member):
            raise BlockedException()
        self.starrers.append(member.id)
        await self.queue_for_update()

    async def remove_star(self, member: discord.Member) -> None:
        """Removes a member's star

        Parameters
        ----------
        member: discord.Member
            The member to remove the star for

        Raises
        ------
        StarException
            Raised if the member given hasn't starred this message
        BlockedException
            Raised if the passed member is blocked from using this guild's starboard
        """
        if member.id not in self.starrers:
            raise StarException("The passed member hasn't starred this message")
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException()
        if await self.starboard.is_ignored(member):
            raise BlockedException()
        self.starrers.remove(member.id)
        await self.queue_for_update()

    def has_starred(self, member: discord.Member) -> bool:
        return member.id in self.starrers

    async def hide(self) -> bool:
        if self.hidden:
            return False
        self.hidden = True
        if self.starboard_message:
            try:
                await self.starboard_message.delete()
            except discord.HTTPException:
                pass
            self.starboard_message = None
        await self.save()
        return True

    async def unhide(self) -> bool:
        if not self.hidden:
            return False
        self.hidden = False
        await self.queue_for_update()
        return True

    async def update_starboard_message(self) -> None:
        self.in_queue = False

        if self.hidden:
            return

        min_stars = await self.starboard.min_stars()
        channel = await self.starboard.channel()
        if channel is None:
            return

        embed = self.build_embed()
        if embed is None:
            return

        if self.stars >= min_stars:
            content = self.STARBOARD_FORMAT.format(stars=self.stars, channel=self.channel, message=self.message)
            if self.starboard_message is not None:
                try:
                    await self.starboard_message.edit(content=content, embed=embed)
                except discord.NotFound:
                    self.starboard_message = None
                    return await self.update_starboard_message()
            else:
                try:
                    self.starboard_message = await channel.send(content=content, embed=embed)
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

        await self.save()
