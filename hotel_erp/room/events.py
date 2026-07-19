"""Room Type document-event handlers (registered in hooks.py doc_events).

Emits room_type.created / room_type.updated / room_type.deleted (contract §4.7)
on Room Type CRUD. "Deleted" means deactivated (active -> 0), per the
contract's own wording ("Room type deactivated") -- Frappe documents are
essentially never hard-deleted once referenced elsewhere (Rate Plan,
Reservation, ...), so deactivation is the real-world equivalent Service B
needs to hear about.
"""
from __future__ import annotations

from hotel_erp.sync.events import enqueue_room_type_event


def on_room_type_after_insert(doc, method=None):
    enqueue_room_type_event("room_type.created", doc.name)


def on_room_type_update(doc, method=None):
    before = doc.get_doc_before_save()
    if before is None:
        # Frappe fires on_update during insert too; after_insert already
        # handled the create case above, so skip it here.
        return
    if before.active and not doc.active:
        enqueue_room_type_event("room_type.deleted", doc.name)
    else:
        enqueue_room_type_event("room_type.updated", doc.name)
