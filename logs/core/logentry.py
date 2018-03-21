from datetime import datetime
from difflib import Differ
from typing import List, Union

import discord

from redbot.core.utils.chat_formatting import box

from logs.core.i18n import _


class LogEntry(discord.Embed):
    def __init__(self, **kwargs):
        self.require_fields = kwargs.pop('require_fields', True)
        kwargs['timestamp'] = kwargs.pop('timestamp', datetime.utcnow())
        super().__init__(**kwargs)
        self._differ = Differ()

    @property
    def is_valid(self):
        """Returns if this LogEntry can be logged"""
        return self.fields or (self.description and not self.require_fields)

    def add_differ_field(self, *, name: str, before: Union[List[str], str], after: Union[List[str], str]):
        """Add a field with a before and after value that's compared using `difflib.Differ`

        This is different from `add_diff_field`, as this automatically compares the two items given,
        instead of the calling code comparing it
        """
        if isinstance(before, str):
            before = before.splitlines()
        if isinstance(after, str):
            after = after.splitlines()

        changed = self._differ.compare(before, after)
        if not changed:
            return
        return self.add_field(name=name, value=box("\n".join(changed), lang="diff"))

    def add_diff_field(self, *, name: str, before, after, box_lang: str = None, inline: bool = False):
        """Add a diff field"""
        before, after = (str(before), str(after))
        if box_lang is not None:
            before = box(before, lang=box_lang)
            after = box(after, lang=box_lang)
        return self.add_field(name=name, inline=inline,
                              value=_("**Before:** {before}\n**After:** {after}").format(before=before, after=after))

    def add_field(self, *, name, value, inline: bool = False):
        if not all([name, value]):
            return
        return super().add_field(name=name, value=value, inline=inline)
