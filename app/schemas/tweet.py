from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserResponse


class TweetResponse(BaseModel):
    id: int
    rawContent: str
    date: datetime | None = None
    user: UserResponse | None = None
    likeCount: int = 0
    retweetCount: int = 0
    replyCount: int = 0
    viewCount: int | None = None
