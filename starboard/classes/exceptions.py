from discord.ext.commands import CommandError


class StarboardException(CommandError):
    """
    Root exception class for all Starboard cog exceptions
    """
    pass


class StarException(StarboardException):
    """
    Raised if a member has already starred or hasn't starred a message
    """
    pass


class NoStarboardEntry(StarboardException):
    """
    Raised if a guild's starboard has no entry for the entry provided
    """
    pass


class HideException(StarboardException):
    """
    Raised if a message either already isn't hidden or has been hidden
    """
    pass


class BlockedException(StarboardException):
    """
    Raised if a passed member is blocked from using a guild's starboard
    """
    pass


class BlockedAuthorException(BlockedException):
    """
    Raised if the message author is blocked from using a guild's starboard
    """
    pass
