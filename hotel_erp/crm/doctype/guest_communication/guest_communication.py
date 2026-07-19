from __future__ import annotations

import frappe
from frappe.model.document import Document


class GuestCommunication(Document):
    def before_insert(self):
        if not self.sent_at:
            self.sent_at = frappe.utils.now_datetime()
