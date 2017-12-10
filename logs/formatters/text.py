from .base import FormatterBase


class TextFormatter(FormatterBase):
    def format(self, title: str, text: str, *, emoji: str, colour, member=None, timestamp=None):
        return "{} **{}**\n**❯** {}".format(emoji or "", title, text)
