from discord.ext.commands import CommandError


class StarboardException(CommandError):
    pass


class StarException(StarboardException):
    pass


class BlockedException(StarboardException):
    pass


class BlockedAuthorException(BlockedException):
    pass


class SelfStarException(BlockedException):
    pass
