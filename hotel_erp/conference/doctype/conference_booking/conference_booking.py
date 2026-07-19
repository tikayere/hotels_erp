from __future__ import annotations

import frappe
from frappe.model.document import Document


class ConferenceBooking(Document):
    def validate(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            frappe.throw("end_at must be after start_at")
