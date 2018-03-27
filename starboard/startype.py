from enum import Enum

from cog_shared.odinair_libs.formatting import normalize

__all__ = ('StarType',)


class StarType(Enum):
    RECEIVED = "received"
    GIVEN = "given"

    def __str__(self):
        return self.value

    @property
    def normalized(self):
        return normalize(str(self))
