from __future__ import annotations

import frappe
from frappe.model.document import Document


class GuestComplaint(Document):
    def before_insert(self):
        if not self.raised_at:
            self.raised_at = frappe.utils.now_datetime()
