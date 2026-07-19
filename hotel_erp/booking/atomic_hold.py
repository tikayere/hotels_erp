"""Atomic check-and-reserve for POST /reservations/hold (contract section 4.5,
NFR-A2: for any date range, concurrent hold requests must never oversell a
room type below zero available rooms on any single night in that range).

Locks every Rate Calendar row (doctype_spec.md section 3) in
[check_in, check_out) for the requested rate_plan, in date order --
deterministic lock order is what prevents deadlocks between two
overlapping-date holds racing each other (hold A for Aug 1-4, hold B for
Aug 3-6 always acquire their shared Aug 3/4 locks in the same relative
order). Checks every night has enough rooms_available before decrementing
any of them; if a single night is short, the whole hold fails and nothing
is decremented (contract section 4.5's note: "if any single night is short,
the whole hold fails with 409 ROOMS_UNAVAILABLE -- never a partial hold").

Unlike the sibling bus project's atomic_hold.py, there is no separate
"confirm" transition here: Rate Calendar tracks an aggregate room count, not
individually-tracked units with a held/booked status each (that distinction
-- which physical room a guest gets -- is Room Assignment, entirely
unrelated to this inventory count, and happens near check-in; contract
section 4.1 principle 3). Once decremented at hold time, the count stays
decremented through confirm; only release/cancel/expiry gives rooms back.

Runs inside the caller's existing DB transaction (the whitelisted API
method that also creates the Reservation Hold document) -- this module
never calls frappe.db.commit() itself.
"""
from __future__ import annotations

from datetime import date, timedelta

import frappe


class RoomsUnavailableError(Exception):
    def __init__(self, unavailable_dates: list[str]):
        self.unavailable_dates = unavailable_dates
        super().__init__(f"Rooms unavailable on: {unavailable_dates}")


def _nights(check_in: date, check_out: date) -> list[date]:
    """[check_in, check_out) -- check_out night itself is not booked, per
    standard hotel convention (the guest departs that morning).
    """
    n = (check_out - check_in).days
    return [check_in + timedelta(days=i) for i in range(n)]


def create_room_hold(rate_plan_id: str, check_in: date, check_out: date, rooms_requested: int) -> None:
    """Raises RoomsUnavailableError, listing every short night (not just the
    first), if the stay cannot be fully satisfied. The caller catches this
    and returns 409 ROOMS_UNAVAILABLE with `details.unavailable_dates`
    populated (contract section 4.9's example error body).
    """
    nights = _nights(check_in, check_out)
    if not nights:
        frappe.throw("check_out must be after check_in")

    rows = frappe.db.sql(
        """
        SELECT date, rooms_available
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        ORDER BY date
        FOR UPDATE
        """,
        {"rate_plan": rate_plan_id, "dates": tuple(nights)},
        as_dict=True,
    )
    by_date = {r.date: r.rooms_available for r in rows}

    # A missing row means 0 available, never "skip this night's check" --
    # doctype_spec.md's Rate Calendar note is explicit that the calendar
    # must be populated far enough ahead that this case shouldn't occur in
    # practice, but the check must fail closed if it ever does.
    unavailable = [str(d) for d in nights if by_date.get(d, 0) < rooms_requested]
    if unavailable:
        raise RoomsUnavailableError(unavailable)

    frappe.db.sql(
        """
        UPDATE `tabRate Calendar`
        SET rooms_available = rooms_available - %(n)s
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_id, "n": rooms_requested, "dates": tuple(nights)},
    )


def release_room_hold(rate_plan_id: str, check_in: date, check_out: date, rooms_requested: int) -> None:
    """Exact inverse of create_room_hold -- called from
    /reservations/{hold_id}/release, /reservations/{id}/cancel, and the
    hold-expiry sweeper (see hold_sweeper.py).
    """
    nights = _nights(check_in, check_out)
    frappe.db.sql(
        """
        UPDATE `tabRate Calendar`
        SET rooms_available = rooms_available + %(n)s
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_id, "n": rooms_requested, "dates": tuple(nights)},
    )
