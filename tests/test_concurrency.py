"""NFR-A2: for any date range, concurrent hold requests must never oversell
a room type below zero available rooms on any single night in that range.

Fires genuinely concurrent HTTP requests (ThreadPoolExecutor, real sockets,
real MariaDB `FOR UPDATE` row locking on the other end) rather than calling
Python functions directly in one thread -- a race condition that can't
occur when everything runs sequentially in-process isn't proof of anything
about the real deployment.
"""
from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor

import requests


def _hold_body(room_type_code: str, rate_plan_code: str, check_in: str, check_out: str, rooms: int = 1) -> dict:
    return {
        "room_type_id": room_type_code,
        "rate_plan_code": rate_plan_code,
        "check_in": check_in,
        "check_out": check_out,
        "rooms_requested": rooms,
        "occupancy": {"adults": 1, "children": 0},
    }


def _post_hold(base_url: str, headers: dict, body: dict, key: str):
    return requests.post(
        f"{base_url}/api/v1/reservations/hold",
        json=body,
        headers={**headers, "Idempotency-Key": key},
        timeout=15,
    )


def test_concurrent_overlapping_holds_never_oversell(
    session, base_url, room_type_code, rate_plan_code, rooms_per_night, api_url
):
    # A date range this test owns exclusively (far enough out that nothing
    # else in the suite touches these exact nights).
    check_in = datetime.date.today() + datetime.timedelta(days=100)
    check_out = check_in + datetime.timedelta(days=2)
    body = _hold_body(room_type_code, rate_plan_code, str(check_in), str(check_out))

    # rooms_per_night + a healthy margin of extra concurrent requesters, all
    # racing for the same nights, one room each -- exactly rooms_per_night of
    # them must win.
    attempts = rooms_per_night + 4
    headers = dict(session.headers)

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        futures = [
            pool.submit(_post_hold, base_url, headers, body, f"concurrency-test-{i}-{check_in}")
            for i in range(attempts)
        ]
        responses = [f.result() for f in futures]

    successes = [r for r in responses if r.status_code == 201]
    conflicts = [r for r in responses if r.status_code == 409]

    assert len(successes) == rooms_per_night, (
        f"expected exactly {rooms_per_night} successful holds (one room each), "
        f"got {len(successes)} successes and {len(conflicts)} conflicts -- "
        f"a wrong count here means the atomic check-and-decrement oversold or undersold"
    )
    assert len(conflicts) == attempts - rooms_per_night
    for r in conflicts:
        assert r.json()["error"]["code"] == "ROOMS_UNAVAILABLE"

    # The requested nights must now show exactly 0 rooms available.
    avail = session.get(
        api_url(
            f"/availability?room_type_id={room_type_code}&check_in={check_in}"
            f"&check_out={check_out}&rooms=1"
        )
    ).json()
    plan = next(q for q in avail["quotes"] if q["rate_plan_code"] == rate_plan_code)
    for night in plan["nightly_rates"]:
        assert night["rooms_available"] == 0, f"{night['date']} should be fully booked, got {night}"

    # Cleanup: release every winning hold to restore inventory for any later run.
    for r in successes:
        hold_id = r.json()["hold_id"]
        session.post(
            api_url(f"/reservations/{hold_id}/release"),
            headers={"Idempotency-Key": f"cleanup-release-{hold_id}"},
        )

    avail_after = session.get(
        api_url(
            f"/availability?room_type_id={room_type_code}&check_in={check_in}"
            f"&check_out={check_out}&rooms=1"
        )
    ).json()
    plan_after = next(q for q in avail_after["quotes"] if q["rate_plan_code"] == rate_plan_code)
    for night in plan_after["nightly_rates"]:
        assert night["rooms_available"] == rooms_per_night, f"release didn't fully restore {night}"


def test_disjoint_date_holds_both_succeed_concurrently(session, base_url, room_type_code, rate_plan_code, api_url):
    # Two holds for non-overlapping date ranges on the *same* room type +
    # rate plan must both succeed even fired at the same instant -- a lock
    # held too coarsely (e.g. the whole rate plan instead of just the
    # requested nights) would wrongly serialize/reject one of these.
    ci_a = datetime.date.today() + datetime.timedelta(days=110)
    co_a = ci_a + datetime.timedelta(days=1)
    ci_b = datetime.date.today() + datetime.timedelta(days=120)
    co_b = ci_b + datetime.timedelta(days=1)

    body_a = _hold_body(room_type_code, rate_plan_code, str(ci_a), str(co_a))
    body_b = _hold_body(room_type_code, rate_plan_code, str(ci_b), str(co_b))
    headers = dict(session.headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_a = pool.submit(_post_hold, base_url, headers, body_a, f"disjoint-a-{ci_a}")
        f_b = pool.submit(_post_hold, base_url, headers, body_b, f"disjoint-b-{ci_b}")
        r_a, r_b = f_a.result(), f_b.result()

    assert r_a.status_code == 201, r_a.text
    assert r_b.status_code == 201, r_b.text

    for r in (r_a, r_b):
        hold_id = r.json()["hold_id"]
        session.post(
            api_url(f"/reservations/{hold_id}/release"),
            headers={"Idempotency-Key": f"cleanup-release-{hold_id}"},
        )
