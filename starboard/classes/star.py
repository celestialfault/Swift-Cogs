from datetime import datetime

import discord

from .exceptions import *
from .starboardbase import StarboardBase


class Star(StarboardBase):
    """Starboard message"""

    def __init__(self, guild, message: discord.Message):
        from .guildstarboard import GuildStarboard
        if not isinstance(guild, GuildStarboard):
            raise ValueError("Expected a GuildStarboard object, received %s" % guild.__class__.__name__)
        self.starboard = guild
        self.message = message
        self.author = message.author
        self.channel = message.channel
        self.starboard_message = None
        self.members = []
        self.hidden = False
        self.last_update = datetime.utcnow()
        # Do not modify these values directly
        self._entry = None  # Modify the above values and use Star.update() instead of modifying this one directly
        self._in_queue = False

    @property
    def user_count(self) -> int:
        return len(self.members)

    @property
    def in_queue(self):
        return self._in_queue

    @in_queue.setter
    def in_queue(self, queue: bool):
        self._in_queue = queue
        if queue:
            self.starboard.queue.put_nowait(self)

    @property
    def exists(self) -> bool:
        return self._entry is not None

    @property
    def can_star(self) -> bool:
        return self.message.content or (self.message.attachments and len(self.message.attachments) > 0)

    @property
    def embed(self):
        if not self.can_star:
            return None
        embed = discord.Embed(colour=discord.Colour.gold(),
                              timestamp=self.message.created_at,
                              description=self.message.content)
        embed.set_author(name=str(self.author), icon_url=self.author.avatar_url)
        if self.message.attachments and len(self.message.attachments) > 0:
            embed.set_image(url=self.message.attachments[0].proxy_url)
        return embed

    def __repr__(self):
        return "<Star stars={0} hidden={1} starboard_msg={2!r} message={3!r} update_queued={4}>".format(
            self.user_count,
            self.hidden,
            self.starboard_message,
            self.message,
            self.in_queue
        )

    async def setup(self, auto_create: bool = False):
        """Setup the current Star object

        You shouldn't need to run this directly, as it's already done for you if you retrieve this with
        either StarboardBase.message or GuildStarboard.message"""
        if self._entry:
            raise RuntimeError("Cannot re-instantiate an already created Star object")
        messages = await self.starboard.config.messages()
        self._entry = discord.utils.find(lambda entry: entry["message_id"] == self.message.id, messages)
        if not self._entry and auto_create:
            await self.create()
        if self._entry:
            self.members = self._entry.get("members", [])
            self.hidden = self._entry.get("hidden", False)
            if self._entry.get("starboard_message", None) is not None:
                channel = await self.starboard.channel()
                try:
                    self.starboard_message = await channel.get_message(self._entry.get("starboard_message", None))
                except discord.NotFound:
                    self.starboard_message = None
                    # force an update to clear the starboard message data
                    await self.save()

    async def create(self):
        """Creates the message's starboard entry

        This is useful if you didn't pass auto_create when creating the Star object"""
        if self._entry:
            raise StarboardException("This message already has an entry")
        self._entry = dict(message_id=self.message.id, channel_id=self.message.channel.id, members=[],
                           starboard_message=None, hidden=False)
        async with self.starboard.config.messages() as messages:
            messages.append(self._entry)
        self.last_update = datetime.utcnow()

    async def save(self, queue_for_update: bool=True):
        """Updates the star's guild starboard entry"""
        if queue_for_update is True:
            self.in_queue = True
        self._entry["members"] = self.members
        self._entry["starboard_message"] = self.starboard_message.id if self.starboard_message is not None else None
        self._entry["hidden"] = self.hidden
        async with self.starboard.config.messages() as messages:
            for message in messages:
                if message["message_id"] == self.message.id:
                    messages[messages.index(message)] = self._entry
                    break

    async def add_star(self, member: discord.Member) -> None:
        """Adds a member's star

        :param member: discord.Member - a member to add the star for
        :raises StarException: If the member has already starred this message
        :raises BlockedException: If the passed member is blocked from the guild's starboard
        :raises BlockedAuthorException: If the author of the message is blocked from using the guild's starboard
        :raises StarboardException: If this message cannot be starred due to lack of content or attachments
        """
        if not self.can_star:
            raise NoMessageContent()
        if member.id in self.members:
            raise StarException("The passed member already starred this message")
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException()
        if await self.starboard.is_ignored(member):
            raise BlockedException()
        self.members.append(member.id)
        await self.save()

    async def remove_star(self, member: discord.Member) -> None:
        """Removes a member's star

        :param member: discord.Member - a member to remove the star for
        :raises: StarException - if the member hasn't starred this message
        :raises: BlockedException - if the passed member is blocked from the guild's starboard
        """
        if member.id not in self.members:
            raise StarException("The passed member hasn't starred this message")
        if await self.starboard.is_ignored(self.author):
            raise BlockedAuthorException()
        if await self.starboard.is_ignored(member):
            raise BlockedException()
        self.members.remove(member.id)
        await self.save()

    def has_starred(self, member: discord.Member) -> bool:
        return member.id in self.members

    async def hide(self):
        if self.hidden:
            raise HideException("This message is already hidden")
        self.hidden = True
        await self.save()
        if self.starboard_message:
            await self.starboard_message.delete()
            self.starboard_message = None

    async def unhide(self):
        if not self.hidden:
            raise HideException("This message isn't currently hidden")
        self.hidden = False
        await self.save()

    async def update_starboard_message(self):
        self.in_queue = False
        if self.hidden:
            return
        min_stars = await self.starboard.min_stars()
        if not self.starboard_message:
            if self.user_count >= min_stars:
                embed = self.embed
                if not embed:
                    return
                channel = await self.starboard.channel()
                if not channel:
                    return
                self.starboard_message = await channel.send(
                    content="⭐ **{}** {}".format(self.user_count, self.channel.mention),
                    embed=embed)
        else:
            if self.user_count < min_stars:
                await self.starboard_message.delete()
                self.starboard_message = None
            else:
                embed = self.embed
                if not embed:
                    return
                await self.starboard_message.edit(content="⭐ **{}** {}".format(self.user_count, self.channel.mention),
                                                  embed=embed)
        await self.save(False)
