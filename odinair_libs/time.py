import re
from collections import OrderedDict
from datetime import timedelta
from typing import Union, Optional

import discord
from discord.ext import commands

__all__ = ('td_format', 'td_seconds', 'FutureTime')


def td_seconds(**kwargs) -> float:
    return timedelta(**kwargs).total_seconds()


time_periods = [
    (td_seconds(days=365), "year"),
    (td_seconds(days=30), "month"),
    (td_seconds(days=7), "week"),
    (td_seconds(days=1), "day"),
    (td_seconds(hours=1), "hour"),
    (td_seconds(minutes=1), "minute"),
    (td_seconds(seconds=1), "second")
]


def td_format(td_object: timedelta, milliseconds: bool = False, append_str: bool = False) -> str:
    """Format a timedelta into a human readable output

    Parameters
    -----------
    td_object: timedelta
        A timedelta object to format
    milliseconds: bool
        If this is True, milliseconds are also appended.

        Note: Milliseconds are rounded to the nearest full number, and as such this may not be fully accurate
    append_str: bool
        Whether or not to append or prepend `in` or `ago` depending on if `td_object` is in the future or past
    """
    # this function is originally from StackOverflow
    # https://stackoverflow.com/a/13756038

    seconds = td_object.total_seconds()
    past = False
    if seconds < 0:
        past = True
        seconds = float(re.sub(r"^-+", "", str(seconds)))
    elif seconds == 0:
        return "0 seconds"

    strs = []

    for period_seconds, period_name in time_periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural = "s" if period_value != 1 else ""
            strs.append(" ".join([str(round(period_value)), f"{period_name}{plural}"]))

    if milliseconds is True:
        ms = round(td_object.microseconds / 1000)
        if ms > 0:
            plural = "s" if ms != 1 else ""
            strs.append(f"{ms} millisecond{plural}")

    built = ", ".join(strs)
    if not append_str:
        return built
    return ("in {}" if not past else "{} ago").format(built)


class FutureTime(timedelta, commands.Converter):
    # The following variables, including `get_seconds`, is originally taken from ZeLarpMaster's Reminders cog
    # https://github.com/ZeLarpMaster/ZeCogs/blob/master/reminder/reminder.py
    # The following changes have been made from the original source:
    #  - Changed TIME_QUANTITIES to use timedelta objects, to be more consistent with td_format
    #  - Added float support, meaning values similar to '0.5h' are accepted,
    #    and converted as if they were given as '30m'
    #  - Properly handle spaces between the duration and time period
    #  - Ported to a proper Converter
    TIME_AMNT_REGEX = re.compile("([0-9]+\.?[0-9]*) ?([a-z]+)", re.IGNORECASE)
    TIME_QUANTITIES = OrderedDict([("seconds", 1.0), ("minutes", 60.0), ("hours", td_seconds(hours=1)),
                                   ("days", td_seconds(days=1)), ("weeks", td_seconds(days=7)),
                                   ("months", td_seconds(days=30)), ("years", td_seconds(days=365))])
    MAX_SECONDS = TIME_QUANTITIES["years"] * 2
    MIN_SECONDS = None
    STRICT_MODE = False

    def __str__(self):
        return self.format()

    def format(self, milliseconds: bool = False):
        return td_format(self, milliseconds=milliseconds)

    @classmethod
    def converter(cls, strict: bool = False, min_duration: Union[str, int, float, None] = None,
                  max_duration: Union[str, int, float, None] = None):
        """Create a FutureTime converter

        Parameters
        -----------
        strict: bool
            If this is True, `convert` will throw a BadArgument exception if the argument passed
            fails to convert into a timedelta, such as if a user didn't give an input, or the
            input is formatted in an invalid fashion.

            Time durations that fail to pass either the min or max duration limits
            will always throw a BadArgument exception regardless of this setting.

            Defaults to ``False``
        min_duration: Union[str, int, float, None]
            The minimum duration that can be given in a conversion. This can be disabled by passing ``None``.
            `str` objects can also be used and will be converted into their appropriate amount of seconds.

            Defaults to ``None``
        max_duration: Union[str, int, float, None]
            How long in seconds to allow for a conversion to go up to.

            Defaults to ``None``
        """
        self = cls.__new__(cls)
        maxs = self.get_seconds(max_duration) if isinstance(max_duration, str) else max_duration
        mins = self.get_seconds(min_duration) if isinstance(min_duration, str) else min_duration

        if isinstance(maxs, (int, float, timedelta)) and maxs <= 0:
            maxs = None
        if isinstance(mins, (int, float, timedelta)) and mins <= 0:
            mins = None

        self.MAX_SECONDS = maxs
        self.MIN_SECONDS = mins

        self.STRICT_MODE = strict
        return self

    @staticmethod
    def get_seconds(time: str) -> Optional[float]:
        """Returns the amount of converted time or None if invalid"""
        seconds = 0
        for time_match in FutureTime.TIME_AMNT_REGEX.finditer(time):
            time_amnt = float(time_match.group(1))
            time_abbrev = time_match.group(2)
            time_quantity = discord.utils.find(lambda t: t[0].startswith(time_abbrev),
                                               FutureTime.TIME_QUANTITIES.items())
            if time_quantity is not None:
                seconds += time_amnt * time_quantity[1]
        return None if seconds == 0 else seconds

    async def convert(self, ctx, argument: str) -> Union[None, "FutureTime"]:
        seconds = self.get_seconds(argument)

        if seconds and self.MAX_SECONDS is not None and seconds > self.MAX_SECONDS:
            raise commands.BadArgument(f'Time duration exceeds maximum of '
                                       f'{td_format(timedelta(seconds=self.MAX_SECONDS))}')
        elif seconds and self.MIN_SECONDS is not None and seconds < self.MIN_SECONDS:
            raise commands.BadArgument(f'Time duration does not exceed minimum of '
                                       f'{td_format(timedelta(seconds=self.MIN_SECONDS))}')

        if seconds is None and self.STRICT_MODE:
            raise commands.BadArgument("Failed to parse duration")
        return type(self)(seconds=seconds) if seconds else None
