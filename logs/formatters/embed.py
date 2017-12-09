from discord import Embed, Colour

from .base import FormatterBase


class EmbedFormatter(FormatterBase):
    def format(self, title: str, text: str, **kwargs):
        embed = Embed(colour=kwargs.get("colour", Colour.greyple()))
        embed.description = text
        embed.set_author(name=title)
        timestamp = kwargs.get("timestamp", None)
        if timestamp:
            embed.timestamp = timestamp
        return embed
