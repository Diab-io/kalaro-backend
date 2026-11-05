from datetime import datetime

from ninja import Schema


class SessionCreateIn(Schema):
    title: str
    scheduled_at: datetime
    duration_minutes: int = 60


class SessionOut(Schema):
    id: int
    title: str
    scheduled_at: datetime
    duration_minutes: int
    meet_link: str
    status: str