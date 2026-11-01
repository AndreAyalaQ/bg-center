from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatTurn:
    role: Role
    content: str
