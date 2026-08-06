"""Reservation document-event handlers (registered in hooks.py doc_events).

Emits the reservation.checked_in / checked_out / no_show webhooks (§4.7) when a
Reservation's status transitions, and enforces that a Room Assignment exists
before a reservation may move to `checked_in` (doctype_spec.md §3 Room
Assignment note). Also triggers the internal-only (FR-A8-A15) housekeeping
auto-assignment workflow on checkout -- that side effect never crosses the
API boundary itself, only the checked_out webhook does.
"""
from __future__ import annotations

import frappe

from hotel_erp.housekeeping.auto_assign import create_checkout_task
from hotel_erp.sync.events import enqueue_reservation_status_event

_STATUS_EVENTS = {
    "checked_in": "reservation.checked_in",
    "checked_out": "reservation.checked_out",
    "no_show": "reservation.no_show",
}


def on_reservation_update(doc, method=None):
    before = doc.get_doc_before_save()
    if before is None or before.status == doc.status:
        return

    if doc.status == "checked_in":
        if not frappe.db.exists("Room Assignment", {"reservation": doc.name}):
            frappe.throw("A Room Assignment must exist before a reservation can be checked in")

    if doc.status == "checked_out":
        create_checkout_task(doc)

    event_type = _STATUS_EVENTS.get(doc.status)
    if event_type:
        enqueue_reservation_status_event(event_type, doc.room_type, doc.name)
