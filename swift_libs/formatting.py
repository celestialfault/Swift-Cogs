import collections
from typing import List, Sequence, Dict

import discord
from redbot.core.bot import Red

from .i18n import lazyi18n, LazyString

__all__ = (
    "normalize",
    "tick",
    "chunks",
    "flatten",
    "trim_to",
    "format_int",
    "slice_dict",
    "index",
    "permissions",
    "cog_name",
    "flatten_values",
    "format_permission",
    "mention",
)

# The values in this dict may act somewhat differently to how you expect:
# `i18n` is a LazyTranslator instance, which means each value is a LazyString object,
# which either must be manually coerced into a str or called once more
# to retrieve the true translated string.
permissions = {
    "add_reactions": lazyi18n("Add Reactions"),
    "administrator": lazyi18n("Administrator"),
    "attach_files": lazyi18n("Attach Files"),
    "ban_members": lazyi18n("Ban Members"),
    "change_nickname": lazyi18n("Change Nickname"),
    "connect": lazyi18n("Connect"),
    "create_instant_invite": lazyi18n("Create Instant Invite"),
    "deafen_members": lazyi18n("Deafen Members"),
    "embed_links": lazyi18n("Embed Links"),
    "external_emojis": lazyi18n("External Emojis"),
    "kick_members": lazyi18n("Kick Members"),
    "manage_channels": lazyi18n("Manage Channels"),
    "manage_emojis": lazyi18n("Manage Emojis"),
    "manage_guild": lazyi18n("Manage Server"),
    "manage_messages": lazyi18n("Manage Messages"),
    "manage_nicknames": lazyi18n("Manage Nicknames"),
    "manage_roles": lazyi18n("Manage Roles"),
    "manage_webhooks": lazyi18n("Manage Webhooks"),
    "mention_everyone": lazyi18n("Mention Everyone"),
    "move_members": lazyi18n("Move Members"),
    "mute_members": lazyi18n("Mute Members"),
    "read_message_history": lazyi18n("Read Message History"),
    "read_messages": lazyi18n("Read Messages"),
    "send_messages": lazyi18n("Send Messages"),
    "send_tts_messages": lazyi18n("Send TTS Messages"),
    "speak": lazyi18n("Speak"),
    "use_voice_activation": lazyi18n("Use Voice Activation"),
    "view_audit_log": lazyi18n("View Audit Log"),
}  # type: Dict[str, LazyString]


def format_permission(perm: str):
    return str(permissions.get(perm, perm.replace("_", " ").title()))


def mention(item):
    if isinstance(item, discord.Role):
        return item.mention if not item.is_default() else item.name
    else:
        return item.mention


def trim_to(text: str, max_len: int):
    """Ensure that `text` is not longer than `max_len` by trimming it"""
    if len(text) <= max_len:
        return text

    text = text.split()
    built = []
    for s in text:
        # If the first string is already over the max length, just fall back to the naive way of
        # trimming strings,
        # and split on the last possible character without regard for if it's actually possible
        # without breaking language semantics
        if len(s) >= max_len and not built:
            return "{}\N{HORIZONTAL ELLIPSIS}".format(s[: max_len - 1])

        built.append(s)

        if len(" ".join(built)) >= max_len:
            return " ".join(built)[: max_len - 1] + "\N{HORIZONTAL ELLIPSIS}"

    return " ".join(built)


def index(seq: Sequence, item):
    """Returns a zero-padded index for `item`"""
    if isinstance(seq, dict):
        seq = list(seq.values())
    item = seq.index(item) + 1
    total_len = len(str(len(seq)))
    padding = "0" * (total_len - len(str(item)))
    return "{}{}".format(padding, item)


def slice_dict(dct: dict, *, max_len: int = 0, chunk_amnt: int = 2) -> List[dict]:
    """Slices a given dict into several dicts

    This moves all the items in each dict chunk into a new dict based on their index
    in the aforementioned chunk.

    This means that a dict similar to {a: a, b: b, c: c, d: d} is turned into
    [{a: a, c: c}, {b: b, d: d}].

    Example usage
    --------------
    >>> slice_dict({'a': 'a', 'b': 'b', 'c': 'c'})
    >>> # => [{'a': 'a', 'c': 'c'}, {'b': 'b'}]

    >>> from random import randint
    >>> dct = dict((str(randint(0, 10000)), randint(0, 10000)) for _ in range(100))
    >>> slice_dict(dct, max_len=20, chunk_amnt=3)
    >>> # => [{'4479': 1195, '5424': 2422, ...}, {'9532': 424, '6269': 2464, ...},
    >>> #     {'7239': 2050, '4747': 5212, ...}]

    Parameters
    ----------
    dct: dict
        The dict to slice
    max_len: int
        The maximum amount of items. If this is greater than zero, the first X items in
        `dct` will be used.
    chunk_amnt: int
        The amount of chunks to slice into
    """
    dct = list(dct.items())
    if max_len > 0:
        dct = dct[:max_len]

    reordered = [[] for _ in range(chunk_amnt)]

    for i in chunks(dct, chunk_amnt):
        for y in i:
            reordered[i.index(y)].append(y)

    return [dict(x) for x in reordered]


def cog_name(bot: Red, name: str):
    """Returns a case-sensitive name from a case-insensitive cog name"""
    return discord.utils.find(lambda x: x.lower() == name.lower(), bot.cogs.keys())


@discord.utils.deprecated()
def format_int(i: int):
    return "{:,}".format(i)


def flatten_values(d):
    items = []
    for k, v in d.items():
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_values(d[k]))
        else:
            items.append(v)
    return items


def flatten(d, parent_key="", *, sep="_"):  # https://stackoverflow.com/a/6027615
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            # noinspection PyUnresolvedReferences
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def tick(text: str):
    """Return `text` with a check mark emoji prepended"""
    return "\N{WHITE HEAVY CHECK MARK} {}".format(text)


def normalize(text, *, title_case: bool = True, underscores: bool = True, **kwargs):
    """Attempts to normalize a string

    Parameters
    -----------
    text: Any
        The string or object to attempt to normalize
    title_case: bool
        Returns the formatted string as a Title Case string. Any substitutions specified as
        keyword arguments are done before the string is converted to title case.
    underscores: bool
        Whether or not underscores are replaced with spaces
    """
    text = str(text)
    if underscores:
        text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text


def chunks(l: Sequence, n: int):  # https://stackoverflow.com/a/312464
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]
