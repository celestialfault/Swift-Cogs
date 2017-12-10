from datetime import datetime

from discord import Embed, Colour, Member

from .base import FormatterBase


class EmbedFormatter(FormatterBase):
    def format(self, title: str, text: str, *, emoji: str, colour: Colour, member: Member=None,
               timestamp: datetime=None):
        embed = Embed(colour=colour or Colour.greyple())
        embed.description = text
        embed.set_author(name=title, icon_url=self.guild.icon_url if not member else
                         member.avatar_url)
        timestamp = timestamp
        if timestamp:
            embed.timestamp = timestamp
        return embed
