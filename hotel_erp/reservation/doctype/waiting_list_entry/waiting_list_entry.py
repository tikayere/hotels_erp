"""Waiting List Entry (FR-A5).

A traveler who hit `409 ROOMS_UNAVAILABLE` on a hold can ask to be waitlisted;
the Aggregator records the request here via POST /api/v1/reservations/waitlist.
Deliberately minimal contact info only (name/phone/email), mirroring
`Reservation Guest`'s privacy shape — identity documents (passport, national
ID) never belong here (NFR-A9 / §5.6).

A scheduled job (hotel_erp.booking.waitlist.check_waitlist) flips `waiting`
entries to `notified` and emits a `waitlist.available` webhook once inventory
frees up; it never holds or reserves anything itself.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class WaitingListEntry(Document):
    def validate(self):
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            frappe.throw("check_out must be after check_in")
        if self.rooms_requested is not None and self.rooms_requested < 1:
            frappe.throw("rooms_requested must be >= 1")
