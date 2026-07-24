import hashlib
import hmac

import requests
from django.conf import settings

PAYSTACK_BASE = "https://api.paystack.co"


def initialize_transaction(*, email: str, amount_kobo: int, reference: str) -> dict:
    resp = requests.post(
        f"{PAYSTACK_BASE}/transaction/initialize",
        headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
        json={"email": email, "amount": amount_kobo, "reference": reference},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("status"):
        raise ValueError(data.get("message", "Paystack initialization failed"))
    return data["data"]  # includes authorization_url, access_code


def verify_transaction(reference: str) -> dict:
    resp = requests.get(
        f"{PAYSTACK_BASE}/transaction/verify/{reference}",
        headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("status"):
        raise ValueError(data.get("message", "Verification failed"))
    return data["data"]  # includes status, amount, currency


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(), body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)