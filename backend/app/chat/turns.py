from typing import Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["user", "assistant"]


class ChatTurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role
    content: str
