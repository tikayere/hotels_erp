from __future__ import annotations

import frappe
from frappe.model.document import Document


class MaintenanceRequest(Document):
    def before_insert(self):
        if not self.opened_at:
            self.opened_at = frappe.utils.now_datetime()
