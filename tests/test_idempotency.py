"""Contract §4.10: replay the same Idempotency-Key + same body -> byte-identical
response; same key + different body -> 409 IDEMPOTENCY_KEY_CONFLICT.
"""
from __future__ import annotations

import datetime


def _future_dates(days_out: int, nights: int = 1):
    ci = datetime.date.today() + datetime.timedelta(days=days_out)
    co = ci + datetime.timedelta(days=nights)
    return str(ci), str(co)


def _hold_body(room_type_code: str, rate_plan_code: str, check_in: str, check_out: str) -> dict:
    return {
        "room_type_id": room_type_code,
        "rate_plan_code": rate_plan_code,
        "check_in": check_in,
        "check_out": check_out,
        "rooms_requested": 1,
        "occupancy": {"adults": 1, "children": 0},
    }


def test_replayed_key_same_body_returns_identical_response(
    session, room_type_code, rate_plan_code, api_url, new_idempotency_key
):
    check_in, check_out = _future_dates(40)
    body = _hold_body(room_type_code, rate_plan_code, check_in, check_out)
    key = new_idempotency_key()

    r1 = session.post(api_url("/reservations/hold"), json=body, headers={"Idempotency-Key": key})
    assert r1.status_code == 201, r1.text
    r2 = session.post(api_url("/reservations/hold"), json=body, headers={"Idempotency-Key": key})
    assert r2.status_code == 201, r2.text
    assert r1.json() == r2.json(), "replaying the same key+body must return the exact stored response"

    # Cleanup: release the hold so this test doesn't permanently consume inventory.
    hold_id = r1.json()["hold_id"]
    session.post(
        api_url(f"/reservations/{hold_id}/release"), headers={"Idempotency-Key": new_idempotency_key()}
    )


def test_replayed_key_different_body_is_conflict(
    session, room_type_code, rate_plan_code, api_url, new_idempotency_key
):
    check_in, check_out = _future_dates(41)
    key = new_idempotency_key()
    body_a = _hold_body(room_type_code, rate_plan_code, check_in, check_out)

    r1 = session.post(api_url("/reservations/hold"), json=body_a, headers={"Idempotency-Key": key})
    assert r1.status_code == 201, r1.text

    body_b = dict(body_a, rooms_requested=2)  # same key, genuinely different request
    r2 = session.post(api_url("/reservations/hold"), json=body_b, headers={"Idempotency-Key": key})
    assert r2.status_code == 409, r2.text
    assert r2.json()["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"

    hold_id = r1.json()["hold_id"]
    session.post(
        api_url(f"/reservations/{hold_id}/release"), headers={"Idempotency-Key": new_idempotency_key()}
    )


def test_missing_idempotency_key_is_rejected(session, room_type_code, rate_plan_code, api_url):
    check_in, check_out = _future_dates(42)
    body = _hold_body(room_type_code, rate_plan_code, check_in, check_out)
    r = session.post(api_url("/reservations/hold"), json=body)  # no Idempotency-Key header
    assert r.status_code >= 400
