"""Pure unit test for hotel_erp/sync/webhook_signing.py -- no Frappe context
or live server needed (the module is plain stdlib hashlib/hmac/time), and
must interop byte-for-byte with the Aggregator's verify.py (round-trip
tested there too -- see hotels_aggregator/tests/unit/test_webhook_verify.py).
"""
from __future__ import annotations

import hashlib
import hmac
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hotel_erp.sync.webhook_signing import sign_webhook_body

SECRET = "shared-secret"
BODY = b'{"event_id": "abc-123", "event_type": "room_type.created"}'


def _verify(secret: str, raw_body: bytes, signature_header: str, timestamp: int) -> bool:
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


def test_signature_has_sha256_prefix():
    sig, ts = sign_webhook_body(SECRET, BODY)
    assert sig.startswith("sha256=")
    assert isinstance(ts, int)


def test_signature_round_trips_with_independent_verification():
    sig, ts = sign_webhook_body(SECRET, BODY)
    assert _verify(SECRET, BODY, sig, ts) is True


def test_signature_uses_provided_timestamp_not_wall_clock():
    fixed_ts = 1234567890
    sig, ts = sign_webhook_body(SECRET, BODY, timestamp=fixed_ts)
    assert ts == fixed_ts
    assert _verify(SECRET, BODY, sig, fixed_ts) is True


def test_different_body_produces_different_signature():
    sig1, ts = sign_webhook_body(SECRET, BODY, timestamp=1234567890)
    sig2, _ = sign_webhook_body(SECRET, b"different body", timestamp=1234567890)
    assert sig1 != sig2


def test_different_secret_produces_different_signature():
    sig1, ts = sign_webhook_body(SECRET, BODY, timestamp=1234567890)
    sig2, _ = sign_webhook_body("a-different-secret", BODY, timestamp=1234567890)
    assert sig1 != sig2
    assert _verify(SECRET, BODY, sig2, 1234567890) is False
