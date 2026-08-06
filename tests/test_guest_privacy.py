"""NFR-A9 / contract §5.6: guest identity documents never cross the API
boundary. The bearer-authenticated service user (hotel_erp/api/auth.py's
SERVICE_USER, "hotel-api@service.local" -- deliberately not Administrator,
see that module's docstring) must not be able to read the Guest DocType at
all, and no /reservations/* response may ever contain passport_no or
national_id.
"""
from __future__ import annotations

import datetime


def test_guest_doctype_is_not_readable_via_the_api_service_user(session, base_url):
    r = session.get(f"{base_url}/api/resource/Guest")
    assert r.status_code in (401, 403), (
        f"expected the API service user to be denied read access to Guest, got "
        f"{r.status_code}: {r.text}"
    )


def test_confirmed_reservation_response_never_contains_guest_pii(
    session, room_type_code, rate_plan_code, api_url
):
    check_in = datetime.date.today() + datetime.timedelta(days=130)
    check_out = check_in + datetime.timedelta(days=1)

    hold_body = {
        "room_type_id": room_type_code,
        "rate_plan_code": rate_plan_code,
        "check_in": str(check_in),
        "check_out": str(check_out),
        "rooms_requested": 1,
        "occupancy": {"adults": 1, "children": 0},
    }
    r_hold = session.post(
        api_url("/reservations/hold"), json=hold_body, headers={"Idempotency-Key": f"privacy-test-{check_in}"}
    )
    assert r_hold.status_code == 201, r_hold.text
    hold_id = r_hold.json()["hold_id"]

    confirm_body = {
        "payment_reference": "test-payment-ref",
        # A real Aggregator payload only ever carries name/phone/email
        # (contract §4.1.8) -- even if a client tried to smuggle a passport
        # number through, it must never come back out in the response.
        "guests": [{"name": "Jane Doe", "phone": "+256700000000", "email": "jane@example.com",
                     "passport_no": "SHOULD-NOT-BE-STORED-OR-RETURNED"}],
    }
    r_confirm = session.post(
        api_url(f"/reservations/{hold_id}/confirm"),
        json=confirm_body,
        headers={"Idempotency-Key": f"privacy-test-confirm-{check_in}"},
    )
    assert r_confirm.status_code == 200, r_confirm.text
    raw = r_confirm.text
    assert "passport" not in raw.lower()
    assert "national_id" not in raw.lower()
    assert "SHOULD-NOT-BE-STORED-OR-RETURNED" not in raw

    body = r_confirm.json()
    for guest in body.get("guests", []):
        assert set(guest.keys()) <= {"name", "phone", "email"}
