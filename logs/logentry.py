import discord

from redbot.core.utils.chat_formatting import box


class LogEntry(discord.Embed):
    def __init__(self, **kwargs):
        self.require_fields = kwargs.pop('require_fields', True)
        super().__init__(**kwargs)

    @property
    def is_valid(self):
        return self.fields or (self.description and not self.require_fields)

    def add_diff_field(self, *, name: str, before, after, description: str = None, box_lang: str = None,
                       inline: bool = False):
        """Add a diff field"""
        before, after = (str(before), str(after))
        if box_lang is not None:
            value = f"**Before:**\n{box(before, lang=box_lang)}\n**After:**\n{box(after, lang=box_lang)}"
        else:
            value = f"**Before:** {before}\n**After:** {after}"
        if description is not None:
            value = f"{description}\n\n{value}"
        return self.add_field(name=name, value=value, inline=inline)

    def add_field(self, *, name, value, inline: bool = False):
        if not all([name, value]):
            return
        return super().add_field(name=name, value=value, inline=inline)
