from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import box

from typing import Optional


class LogEntry:
    def __init__(self, group, require_fields: bool=True, colour: discord.Colour=None):
        self.group = group
        self.guild = group.guild
        self.require_fields = require_fields  # Set this to False to allow sending a log message with just a description
        # Visible on text + embeds
        self.title = discord.Embed.Empty
        self.description = discord.Embed.Empty
        self.fields = []
        self.footer = discord.Embed.Empty
        # Visible on text
        self.emoji = None
        # Visible on embeds
        self.icon_url = self.guild.guild.icon_url
        self.timestamp = discord.Embed.Empty
        self.colour = colour or discord.Embed.Empty

    def set_title(self, title: str, icon_url: str=None, emoji: str=None):
        """Set the title, icon url and/or emoji. Returns self for chaining"""
        self.title = title
        if icon_url:
            self.icon_url = icon_url
        if emoji:
            self.emoji = emoji
        return self

    def set_footer(self, footer: str=None, timestamp: datetime=None):
        """Set the title and/or timestamp"""
        if footer:
            self.footer = footer
        if timestamp:
            self.timestamp = timestamp

    def add_diff_field(self, title: str, before, after, description: str=None, box_lang: str=None):
        """Adds a before and after field"""
        before = str(before)
        after = str(after)
        if box_lang is not None:
            value = "**Before**:\n{}\n**After:**\n{}".format(box(before, lang=box_lang), box(after, lang=box_lang))
        else:
            value = "**Before:** {}\n**After:** {}".format(before, after)
        if description is not None:
            value = "{}\n\n{}".format(description, value)
        self.add_field(title=title, value=value)

    def add_field(self, title: str, value, inline: bool = False):
        """Add a field to the current LogEntry"""
        if title is None or value is None:
            return self
        value = str(value)
        self.fields.append([title, value, inline])

    def format(self) -> Optional[discord.Embed]:
        """Format the current LogEntry into a usable log message.

        If this LogEntry is improperly setup or has no content, this will instead return None
        """
        if self.title is None:  # require a title
            return None
        if not len(self.fields) and not self.description:  # require at least one field or a description
            return None
        if self.require_fields and not len(self.fields):  # check if allowing no fields is enabled
            return None

        embed = discord.Embed(colour=self.colour, timestamp=self.timestamp, description=self.description)
        embed.set_footer(text=self.footer)
        embed.set_author(name=self.title, icon_url=self.icon_url)
        for title, text, inline in self.fields:
            if title is None or text is None:
                continue
            if not title.rstrip() or not text.rstrip():
                continue
            embed.add_field(name=title, value=text, inline=inline)
        return embed
