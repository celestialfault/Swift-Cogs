from typing import List

import discord

from logs.logentry import LogEntry
from logs.utils import difference
from .base import LogType


def format_emoji(emoji: discord.Emoji, removed: bool=False):
    if not removed:
        ret = "{0!s} ({1}**{0.name}**{1})"
    else:
        ret = "{1}**{0.name}**{1}"
    return ret.format(emoji, ":" if emoji.require_colons else "")


class EmojiLogType(LogType):
    name = "emoji"

    def update(self, before: List[discord.Emoji], after: List[discord.Emoji], **kwargs):
        added, removed = difference(before, after)

        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Guild emojis updated", emoji="\N{MEMO}")

        if len(added):
            ret.add_field(title="Emoji{} Added".format("s" if len(added) > 1 else ""),
                          value="\n".join(format_emoji(x) for x in added))
        if len(removed):
            ret.add_field(title="Emoji{} Removed".format("s" if len(removed) > 1 else ""),
                          value="\n".join(format_emoji(x, True) for x in removed))

        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
