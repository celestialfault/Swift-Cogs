from .base import FormatterBase


class TextFormatter(FormatterBase):
    def format(self, title: str, text: str, **kwargs):
        return "{} **{}**\n**❯** {}".format(kwargs.get("emoji", ""), title, text)
