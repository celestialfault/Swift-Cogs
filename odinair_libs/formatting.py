import collections
from typing import List, Any, Sequence

__all__ = ("normalize", "tick", "chunks", "flatten", "trim_to",
           "simple_table", "format_int", "slice_dict", "index")


def simple_table(l1: List[str], l2: List[Any]):
    # this is actually just two space-separated joined lists, not even a proper table lol
    if len(l1) != len(l2):
        raise ValueError('length of l1 and l2 are not equal')
    max_len = max([len(x) for x in l1])
    return ["{}{}{}".format(x, ' ' * ((max_len - len(x)) + 2), l2[l1.index(x)]) for x in l1]


def trim_to(text: str, max_len: int):
    """Ensure that `text` is not longer than `max_len` by trimming it"""
    if len(text) <= max_len:
        return text

    text = text.split()
    built = []
    for s in text:
        # If the first string is already over the max length, just fall back to the naive way of trimming strings,
        # and split on the last possible character without regard for if it's actually possible
        # without breaking language semantics
        if len(s) >= max_len and not built:
            return "{}\N{HORIZONTAL ELLIPSIS}".format(s[:max_len - 1])

        built.append(s)

        if len(" ".join(built)) >= max_len:
            return " ".join(built)[:max_len - 1] + "\N{HORIZONTAL ELLIPSIS}"

    return " ".join(built)


def index(seq: Sequence, item):
    """Returns a zero-padded index for `item`"""
    if isinstance(seq, dict):
        seq = list(seq.values())
    item = seq.index(item) + 1
    total_len = len(str(len(seq)))
    padding = "0" * (total_len - len(str(item)))
    return "{}{}".format(padding, item)


def slice_dict(dct: dict, *, max_len: int = 0, chunk_amnt: int = 2, reorder: bool = True) -> List[dict]:
    """Slices a given dict into several dicts

    If reorder is False, this acts similarly to the following:
    >>> [dict(x) for x in chunks(list(dict().items()), 2)]

    Otherwise, this moves all the items in each chunked dict into a new dict based on their index
    in the aforementioned chunked dict.

    This means that a dict similar to {a: a, b: b, c: c, d: d} is turned into [{a: a, c: c}, {b: b, d: d}].

    Example usage
    --------------
    >>> slice_dict({'a': 'a', 'b': 'b', 'c': 'c'})
    >>> # => [{'a': 'a', 'c': 'c'}, {'b': 'b'}]

    >>> slice_dict({'a': 'a', 'b': 'b', 'c': 'c'}, reorder=False)
    >>> # => [{'a': 'a', 'b': 'b'}, {'c': 'c'}]

    >>> from random import randint
    >>> dct = dict((str(randint(0, 10000)), randint(0, 10000)) for x in range(100))
    >>> slice_dict(dct, max_len=20, chunk_amnt=3)
    >>> # => [{'4479': 1195, '5424': 2422, ...}, {'9532': 424, '6269': 2464, ...}, {'7239': 2050, '4747': 5212, ...}]

    Parameters
    ----------
    dct: dict
        The dict to slice
    max_len: int
        The maximum amount of items. If this is greater than zero, the first X items in
        `dct` will be used.
    chunk_amnt: int
        The amount of chunks to slice into
    reorder: bool
        Whether or not items are reordered in the returned values
        based on their index in the chunked dicts
    """
    dct = list(dct.items())
    if max_len > 0:
        dct = dct[:max_len]

    if reorder is False:
        return [dict(x) for x in chunks(dct, chunk_amnt)]

    dct_ = [[] for _ in range(chunk_amnt)]

    for i in chunks(dct, chunk_amnt):
        for y in i:
            dct_[i.index(y)].append(y)

    return [dict(x) for x in dct_]


def format_int(i: int):
    return "".join(reversed(",".join(chunks("".join(reversed(str(i))), 3))))


def flatten(d, parent_key='', *, sep='_'):  # https://stackoverflow.com/a/6027615
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
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
        Returns the formatted string as a Title Case string. Any substitutions specified as keyword arguments are done
        before the string is title cased.
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
        yield l[i:i + n]
