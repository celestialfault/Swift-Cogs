"""Various miscellaneous helper functions & classes"""

from asyncio import Queue
from typing import Iterable

__all__ = ("IterQueue",)


class IterQueue(Queue, Iterable):
    """Iterable version of an asyncio Queue"""

    def __iter__(self):
        while not self.empty():
            yield self.get_nowait()
