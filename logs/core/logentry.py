from datetime import datetime
from difflib import Differ
from typing import List, Tuple

import discord

from redbot.core.utils.chat_formatting import box

from logs.core.i18n import i18n


def translate_common_types(var):
    if var is None:
        return i18n("None")
    elif var is False:
        return i18n("False")
    elif var is True:
        return i18n("True")
    else:
        return str(var)


class LogEntry(discord.Embed):

    def __init__(self, module, **kwargs):
        self.module = module
        self.require_fields = kwargs.pop("require_fields", True)
        self.ignore_fields = kwargs.pop("ignore_fields", [])
        kwargs["timestamp"] = kwargs.pop("timestamp", datetime.utcnow())
        super().__init__(**kwargs)

    @property
    def is_valid(self):
        return any(
            [
                [x for x in self.fields if x.name not in self.ignore_fields],
                self.description and not self.require_fields,
            ]
        )

    async def send(self, send_to: discord.abc.Messageable, **kwargs):
        if not self.is_valid:
            return
        await send_to.send(embed=self, **kwargs)

    async def add_if_changed(
        self,
        *,
        name: str,
        before,
        after,
        diff: bool = False,
        box_lang: str = None,
        inline: bool = False,
        converter=None,
        config_opt: Tuple[str, ...] = None
    ):
        if diff and not (isinstance(before, (List, str)) and isinstance(after, (List, str))):
            raise ValueError(
                "diff rendering is enabled and before and/or after are not of either "
                "list or str types"
            )
        if before == after:
            return self
        if config_opt and not await self.module.is_opt_enabled(*config_opt):
            return self
        if converter is not None:
            before, after = (converter(before), converter(after))
        self.add_diff_field(
            name=name, before=before, after=after, box_lang=box_lang, inline=inline, diff=diff
        )

    def add_diff_field(
        self,
        *,
        name: str,
        before,
        after,
        box_lang: str = None,
        inline: bool = False,
        diff: bool = False
    ):
        if diff:
            if isinstance(before, str):
                before = before.splitlines()
            if isinstance(after, str):
                after = after.splitlines()

            changed = Differ().compare(before, after)
            if not changed:
                return self
            return self.add_field(
                name=name, value=box("\n".join(changed), lang="diff"), inline=inline
            )

        before, after = (translate_common_types(before), translate_common_types(after))
        if box_lang is not None:
            before = box(before, lang=box_lang)
            after = box(after, lang=box_lang)
        return self.add_field(
            name=name,
            inline=inline,
            value=i18n("**Before:** {before}\n" "**After:** {after}").format(
                before=before, after=after
            ),
        )

    def add_field(self, *, name, value, inline: bool = False):
        if not all([name, value]):
            return self
        return super().add_field(name=name, value=value, inline=inline)
