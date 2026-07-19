"""Waiting List (FR-A5).

`check_waitlist` runs on the 1-minute scheduler (alongside the hold sweeper):
for every `Waiting List Entry` still `waiting`, it checks whether the rate
plan now has `rooms_available >= rooms_requested` on *every* night of the
requested stay. If so it flips the entry to `notified` and emits a
`waitlist.available` webhook so the Aggregator can notify the traveler. It
does NOT hold or reserve anything — detection and flagging only; the traveler
still has to race everyone else to the normal /reservations/hold path.

The `waitlist.available` event carries IDs and dates only — never the entry's
contact info — for the same reason `reservation.checked_in` carries only IDs
(§4.7 note / §5.6): the event exists so Service B can trigger its own traveler
notification, it is not itself the notification and carries no PII.
"""
from __future__ import annotations

from datetime import date, timedelta

import frappe

from hotel_erp.sync.events import enqueue_event, namespaced


def _nights(check_in: date, check_out: date) -> list[date]:
    n = (check_out - check_in).days
    return [check_in + timedelta(days=i) for i in range(n)]


def _stay_available(rate_plan_name: str, check_in: date, check_out: date, rooms_requested: int) -> bool:
    """True only if every night in [check_in, check_out) has enough rooms. A
    missing Rate Calendar row means 0 available (same fail-closed rule as
    atomic_hold), so the stay is not considered available."""
    nights = _nights(check_in, check_out)
    if not nights:
        return False
    rows = frappe.db.sql(
        """
        SELECT date, rooms_available
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_name, "dates": tuple(nights)},
        as_dict=True,
    )
    by_date = {r.date: r.rooms_available for r in rows}
    return all(by_date.get(n, 0) >= rooms_requested for n in nights)


def check_waitlist() -> None:
    entries = frappe.get_all(
        "Waiting List Entry",
        filters={"status": "waiting"},
        fields=["name", "room_type", "rate_plan", "check_in", "check_out", "rooms_requested"],
    )
    for entry in entries:
        ci = frappe.utils.getdate(entry.check_in)
        co = frappe.utils.getdate(entry.check_out)
        if not _stay_available(entry.rate_plan, ci, co, entry.rooms_requested):
            continue

        frappe.db.set_value("Waiting List Entry", entry.name, "status", "notified")
        room_type_code = frappe.db.get_value("Room Type", entry.room_type, "code")
        rate_plan_code = frappe.db.get_value("Rate Plan", entry.rate_plan, "code")
        enqueue_event(
            "waitlist.available",
            {
                "room_type_id": namespaced(room_type_code),
                "rate_plan_code": rate_plan_code,
                "check_in": str(ci),
                "check_out": str(co),
            },
        )
        # Commit per-entry so a crash mid-sweep can't undo notifications already
        # emitted (same reasoning as hold_sweeper's per-hold commit).
        frappe.db.commit()
