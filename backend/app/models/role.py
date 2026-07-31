from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]
