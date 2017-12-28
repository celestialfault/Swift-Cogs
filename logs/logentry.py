import discord
from redbot.core.utils.chat_formatting import escape

from typing import Union, Optional
from enum import Enum


class LogFormat(Enum):
    EMBED = "EMBED"
    TEXT = "TEXT"

    def __str__(self):
        return self.value


class LogEntry:
    def __init__(self, group, guild=None):
        self.group = group
        self.guild = guild or group.guild
        self.title = None
        self.emoji = None
        self.timestamp = discord.Embed.Empty
        self.description = discord.Embed.Empty
        self.colour = discord.Embed.Empty
        self.icon_url = None
        self.footer = discord.Embed.Empty
        self.require_fields = True  # Set this to False to allow sending a log message with just a description
        self.fields = []

    def add_field(self, title: str, value: str):
        """Add a field to the Log entry, returns self for chaining"""
        self.fields.append([title, value])
        return self

    def format(self, log_format: LogFormat) -> Optional[Union[str, discord.Embed]]:
        """Format the current LogEntry into a usable log message.

        Returns either `str` or `discord.Embed` based on the passed log format"""
        if self.title is None:
            raise RuntimeError("Log entry has no title set")
        if not len(self.fields) and not self.description:
            return None
        if self.require_fields and not len(self.fields):
            return None
        if str(log_format) == "EMBED":
            embed = discord.Embed(colour=self.colour, timestamp=self.timestamp, description=self.description)
            embed.set_footer(text=self.footer)
            title = "[{}] {}".format(self.group.name.title(), self.title)
            embed.set_author(name=title, icon_url=self.icon_url or self.guild.guild.icon_url)
            for title, text in self.fields:
                if not title or not text:
                    continue
                embed.add_field(name=title, value=text, inline=False)
            return embed
        elif str(log_format) == "TEXT":
            field_txt = "\n\n".join(["**❯ {}**\n{}".format(escape(x, mass_mentions=True), escape(y, mass_mentions=True))
                                     for x, y in self.fields])
            description = "\n{}" if self.description else ""
            return "{} [**{}**] **{}**{}\n\n{}".format(self.emoji, self.group.name.title(), description, self.title,
                                                       field_txt)
        else:
            raise ValueError("Unknown log format '{}'".format(str(log_format)))
