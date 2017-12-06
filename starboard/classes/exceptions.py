class StarboardException(Exception):
    """
    Super exception for all Starboard exceptions
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
