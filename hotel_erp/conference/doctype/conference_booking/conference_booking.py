from __future__ import annotations

import frappe
from frappe.model.document import Document

from hotel_erp.finance.billing import post_conference_revenue


class ConferenceBooking(Document):
    def validate(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            frappe.throw("end_at must be after start_at")
        self._check_venue_conflict()

    def _check_venue_conflict(self):
        """A hotel typically has one (or a handful of) conference/meeting
        room(s) -- double-booking the same space for overlapping times is a
        real operational failure a front-desk agent should be blocked from
        making, not just warned about. Cancelled bookings never conflict."""
        if not (self.space_name and self.start_at and self.end_at):
            return
        overlapping = frappe.get_all(
            "Conference Booking",
            filters={
                "name": ["!=", self.name or ""],
                "space_name": self.space_name,
                "status": ["!=", "cancelled"],
                "start_at": ["<", self.end_at],
                "end_at": [">", self.start_at],
            },
            fields=["name"],
            limit=1,
        )
        if overlapping:
            frappe.throw(
                f"{self.space_name} is already booked ({overlapping[0].name}) for an overlapping time"
            )

    def on_update(self):
        before = self.get_doc_before_save()
        if before is None or before.status == self.status:
            return
        if self.status == "confirmed":
            post_conference_revenue(self)
