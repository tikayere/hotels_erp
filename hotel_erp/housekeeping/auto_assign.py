"""Housekeeping auto-assignment (FR-A9 internal workflow).

Called from `hotel_erp.reservation.events.on_reservation_update` the moment
a Reservation transitions to `checked_out`: the room needs cleaning before
it can be sold again, so this creates the cleaning task and flips the room
to `dirty` in the same step a real front-desk/housekeeping handoff would --
nothing waits on a human to notice the checkout happened.
"""
from __future__ import annotations

import frappe

from hotel_erp.hr.staff_assignment import pick_least_loaded_staff

_OPEN_TASK_STATUSES = ["pending", "in_progress"]


def create_checkout_task(reservation) -> None:
    room_name = _room_for_reservation(reservation)
    if not room_name:
        # No Room Assignment on this reservation (shouldn't happen -- checked_in
        # requires one, per reservation/events.py -- but fail soft rather than
        # blocking the checkout transition over a missing housekeeping task).
        return

    frappe.db.set_value("Room", room_name, "status", "dirty")

    assignee = pick_least_loaded_staff(
        department="Housekeeping",
        open_task_doctype="Housekeeping Task",
        assignee_field="assigned_to",
        open_status_field="status",
        open_statuses=_OPEN_TASK_STATUSES,
    )

    frappe.get_doc(
        {
            "doctype": "Housekeeping Task",
            "room": room_name,
            "type": "cleaning",
            "status": "pending",
            "assigned_to": assignee,
            "due_at": frappe.utils.now_datetime(),
            "notes": f"Auto-created on checkout of {reservation.name}",
        }
    ).insert(ignore_permissions=True)


def _room_for_reservation(reservation) -> str | None:
    return frappe.db.get_value("Room Assignment", {"reservation": reservation.name}, "room")
