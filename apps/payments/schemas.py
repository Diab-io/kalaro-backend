from ninja import Schema
from datetime import datetime

class InitializePaymentIn(Schema):
    course_id: int


class InitializePaymentOut(Schema):
    authorization_url: str
    reference: str


class ManualPaymentIn(Schema):
    course_id: int
    bank_reference: str = ""


class ManualReviewIn(Schema):
    approve: bool
    note: str = ""


class OrderOut(Schema):
    id: int
    reference: str
    amount: float
    currency: str
    status: str
    course_id: int


class EnrollmentOut(Schema):
    id: int
    course_id: int
    status: str
    source: str
    enrolled_at: datetime