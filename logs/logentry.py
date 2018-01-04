from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape, box

from typing import Union, Optional
from enum import Enum


class LogFormat(Enum):
    EMBED = "EMBED"
    TEXT = "TEXT"

    def __str__(self):
        return self.value


class LogEntry:
    def __init__(self, group, title: str=None, emoji: str=None, description: str=None, colour: discord.Colour=None,
                 timestamp: datetime=None, require_fields: bool=True):
        self.group = group
        self.guild = group.guild
        self.title = title
        self.emoji = emoji
        self.icon_url = None
        self.timestamp = timestamp or discord.Embed.Empty
        self.description = description or discord.Embed.Empty
        self.colour = colour or discord.Embed.Empty
        self.footer = discord.Embed.Empty
        self.require_fields = require_fields  # Set this to False to allow sending a log message with just a description
        self.fields = []

    def add_diff_field(self, title: str, before, after, description: str=None, box_lang: str=None):
        """Adds a before/after field, returns self for chaining"""
        before = str(before)
        after = str(after)
        if box_lang is not None:
            value = "**Before**:\n{}\n**After:**\n{}".format(box(before, lang=box_lang),
                                                             box(after, lang=box_lang))
        else:
            value = "**Before:** {}\n**After:** {}".format(before, after)
        if description is not None:
            value = "{}\n\n{}".format(description, value)
        return self.add_field(title=title, value=value)

    def add_field(self, title: str, value: str):
        """Add a field to the Log entry, returns self for chaining"""
        if title is None or value is None:
            return self
        self.fields.append([title, value])
        return self

    def format(self, log_format: LogFormat) -> Optional[Union[str, discord.Embed]]:
        """Format the current LogEntry into a usable log message.

        Returns either `str` or `discord.Embed` based on the passed log format"""
        if self.title is None:  # require a title
            raise RuntimeError("Log entry has no title set")
        if not len(self.fields) and not self.description:  # require at least one field or a description
            return None
        if self.require_fields and not len(self.fields):  # check if allowing no fields is enabled
            return None
        if str(log_format) == "EMBED":
            embed = discord.Embed(colour=self.colour, timestamp=self.timestamp, description=self.description)
            embed.set_footer(text=self.footer)
            embed.set_author(name=self.title, icon_url=self.icon_url or self.guild.guild.icon_url)
            for title, text in self.fields:
                if title is None or text is None:
                    continue
                if not title.rstrip() or not text.rstrip():
                    continue
                embed.add_field(name=title, value=text, inline=False)
            return embed
        elif str(log_format) == "TEXT":
            field_txt = "\n\n".join(["**❯ {}**\n{}".format(escape(x, mass_mentions=True).rstrip(),
                                                           escape(y, mass_mentions=True).rstrip())
                                     for x, y in self.fields if x is not None and y is not None
                                     and x.rstrip() and y.rstrip()])
            description = "\n{}".format(escape(self.description, mass_mentions=True)) if self.description else ""
            return "{} **{}**{}\n\n{}".format(self.emoji, self.title, description, field_txt)
        else:
            raise ValueError("Unknown log format '{}'".format(str(log_format)))
