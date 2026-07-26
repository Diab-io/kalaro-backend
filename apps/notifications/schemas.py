from ninja import Schema


class NotificationOut(Schema):
    id: int
    type: str
    title: str
    body: str
    link: str
    read_at: str | None
    created_at: str