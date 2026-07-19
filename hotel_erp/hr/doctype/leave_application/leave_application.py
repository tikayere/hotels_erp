from __future__ import annotations

import frappe
from frappe.model.document import Document


class LeaveApplication(Document):
    def validate(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            frappe.throw("to_date must be on or after from_date")
