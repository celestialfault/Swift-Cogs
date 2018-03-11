from typing import Union, Optional

from collections import OrderedDict
from datetime import timedelta

import re

import discord
from discord.ext import commands

from odinair_libs.formatting import td_format

__all__ = ["FutureTime", "get_role_or_member"]


def get_role_or_member(snowflake: int, guild: discord.Guild):
    return guild.get_member(snowflake) or discord.utils.get(guild.roles, id=snowflake)


def td_seconds(**kwargs) -> float:
    return timedelta(**kwargs).total_seconds()


# I'm sorry for this abomination of a misuse of subclassing
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

    def format(self, short_format: bool = False, milliseconds: bool = False):
        return td_format(self, short_format=short_format, milliseconds=milliseconds)

    @classmethod
    def converter(cls, strict: bool = False, min_duration: Union[str, int, float, None] = None,
                  max_duration: Union[str, int, float, None] = "2y"):
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

            Defaults to ``"2y"``
        """
        self = cls.__new__(cls)
        self.MAX_SECONDS = self.get_seconds(max_duration) if isinstance(max_duration, str) else max_duration
        self.MIN_SECONDS = self.get_seconds(min_duration) if isinstance(min_duration, str) else min_duration
        self.STRICT_MODE = strict
        return self

    @staticmethod
    def get_seconds(time: str) -> Optional[int]:
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

    @classmethod
    async def convert(cls, ctx, argument: str) -> Union[None, timedelta]:
        seconds = cls.get_seconds(argument)

        if seconds and cls.MAX_SECONDS is not None and seconds > cls.MAX_SECONDS:
            raise commands.BadArgument('Time duration exceeds {}'.format(
                td_format(timedelta(seconds=cls.MAX_SECONDS))))
        elif seconds and cls.MIN_SECONDS is not None and seconds < cls.MIN_SECONDS:
            raise commands.BadArgument('Time duration does not exceed minimum of {}'.format(
                td_format(timedelta(seconds=cls.MIN_SECONDS))))

        if seconds is None and cls.STRICT_MODE:
            raise commands.BadArgument("Failed to parse duration")
        return cls(seconds=seconds) if seconds else None
