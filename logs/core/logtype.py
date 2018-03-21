from enum import Enum


class LogType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    def __str__(self):
        return str(self.value)
