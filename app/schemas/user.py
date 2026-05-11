from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str
    displayname: str
    description: str | None = None
    followersCount: int = 0
    friendsCount: int = 0
    statusesCount: int = 0
    createdAt: datetime | None = None
    verified: bool = False
