"""Night audit (FR-A8-A15 internal workflow) -- registered as a daily
scheduled job in hooks.py, meant to run once after the hotel's last
check-in window for the day has closed.

Its one responsibility here: flag no-shows. A `confirmed` reservation whose
check_in date has already passed without the guest ever checking in is a
no-show -- going through `doc.save()` (not a raw UPDATE) so the existing
`reservation.events.on_reservation_update` hook fires the
`reservation.no_show` webhook (§4.7) exactly the same way a manually-marked
no-show would.

No inventory is released: per `booking/atomic_hold.py`'s own docstring,
Rate Calendar stays decremented from hold through confirm regardless of
what happens afterward -- a no-show is a revenue event, not a
cancellation, so the room correctly stays "sold" for those nights.
"""
from __future__ import annotations

import frappe


def run_night_audit() -> None:
    today = frappe.utils.getdate()
    overdue = frappe.get_all(
        "Reservation",
        filters={"status": "confirmed", "check_in": ["<", today]},
        pluck="name",
    )
    for name in overdue:
        doc = frappe.get_doc("Reservation", name)
        doc.status = "no_show"
        doc.save(ignore_permissions=True)
        # Commit per-reservation, matching hold_sweeper's reasoning: a crash
        # partway through a large audit batch must not roll back no-shows
        # already correctly flagged (and their webhooks already enqueued).
        frappe.db.commit()
