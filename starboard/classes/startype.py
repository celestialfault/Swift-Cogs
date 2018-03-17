from enum import Enum

from odinair_libs.formatting import normalize


class StarType(Enum):
    RECEIVED = "received"
    GIVEN = "given"

    def __str__(self):
        return self.value

    @property
    def normalized(self):
        return normalize(str(self))
