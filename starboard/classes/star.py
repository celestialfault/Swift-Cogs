import discord

from .exceptions import *
from .starboardbase import StarboardBase


class Star(StarboardBase):
    """
    Starboard wrapper for a Message object

    Don't create this directly - use GuildStarboard.message to create this
    """

    def __init__(self, guild, message: discord.Message):
        super().__init__()
        from .guildstarboard import GuildStarboard
        if not isinstance(guild, GuildStarboard):
            raise ValueError("Expected a GuildStarboard object, received %s" % guild.__class__.__name__)
        self.guild = guild
        self.message = message
        self.author = message.author
        self.channel = message.channel
        self.starboard_message = None
        self.members = []
        self.hidden = False
        # Do not modify this directly - modify the above values
        self._entry = None

    @property
    def user_count(self):
        return len(self.members)

    @property
    def entry_exists(self):
        return self._entry is not None

    @property
    def embed(self):
        embed = discord.Embed(colour=discord.Colour.gold(),
                              timestamp=self.message.created_at)
        embed.set_author(name=str(self.author), icon_url=self.author.avatar_url)
        embed.description = self.message.content
        if self.message.attachments and len(self.message.attachments) > 0:
            embed.set_image(url=self.message.attachments[0].proxy_url)
        return embed

    async def setup(self, *, auto_create: bool = False):
        """
        Setup the current Star object

        You shouldn't run this directly, as it's already done for you if you retrieve these with StarboardBase.message
        or GuildStarboard.message
        """
        messages = await self.guild.config.messages()
        self._entry = discord.utils.find(lambda entry: entry["message_id"] == self.message.id, messages)
        if not self._entry and auto_create:
            await self.create()
        if self._entry:
            self.members = self._entry["members"]
            self.hidden = self._entry["hidden"]
            if self._entry["starboard_message"]:
                channel = await self.guild.channel()
                if channel:
                    self.starboard_message = await channel.get_message(self._entry["starboard_message"])

    async def create(self):
        """
        Creates the message's starboard entry

        This is useful if you didn't pass auto_create when creating the Star object
        """
        if self._entry:
            raise StarboardException("This message already has an entry")
        self._entry = dict(message_id=self.message.id, channel_id=self.message.channel.id, members=[],
                           starboard_message=None, hidden=False)
        async with self.guild.config.messages() as messages:
            messages.append(self._entry)

    async def update(self):
        """
        Updates the star's guild starboard entry
        """
        # noinspection PyBroadException
        try:
            await self.update_starboard_message()
        except Exception as e:
            print(e)
            pass
        self._entry["members"] = self.members
        self._entry["starboard_message"] = self.starboard_message.id if self.starboard_message else None
        self._entry["hidden"] = self.hidden
        async with self.guild.config.messages() as messages:
            for message in messages:
                if message["message_id"] == self.message.id:
                    messages[messages.index(message)] = self._entry

    async def add(self, member: discord.Member) -> None:
        """
        Adds a member's star

        :param member: discord.Member - a member to add the star for
        :return: None
        :raises: StarException - if the member has already starred this message
        """
        if member.id in self.members:
            raise StarException("The passed member already starred this message")
        self.members.append(member.id)
        await self.update()

    async def remove(self, member: discord.Member) -> None:
        """
        Removes a member's star

        :param member: discord.Member - a member to remove the star for
        :return: None
        :raises: StarException - if the member hasn't starred this message
        """
        if member.id not in self.members:
            raise StarException("The passed member hasn't starred this message")
        del self.members[self.members.index(member.id)]
        await self.update()

    async def hide(self):
        if self.hidden:
            raise HideException("This message is already hidden")
        self.hidden = True
        await self.update()
        if self.starboard_message:
            await self.starboard_message.delete()

    async def unhide(self):
        if not self.hidden:
            raise HideException("This message currently isn't hidden")
        self.hidden = False
        await self.update()

    async def update_starboard_message(self):
        if self.hidden:
            return
        min_stars = await self.guild.min_stars()
        # This might be a terrible idea, but this was made in one night
        # So what's the worst that could happen?
        # [ not pictured: an entire planet blowing up ]
        if not self.starboard_message:
            if self.user_count >= min_stars:
                channel = await self.guild.channel()
                if not channel:
                    return
                self.starboard_message = await channel.send(
                    content="⭐ **{}** {}".format(self.user_count, self.channel.mention),
                    embed=self.embed)
        else:
            if self.user_count < min_stars:
                await self.starboard_message.delete()
                self.starboard_message = None
            else:
                await self.starboard_message.edit(content="⭐ **{}** {}".format(self.user_count, self.channel.mention),
                                                  embed=self.embed)
