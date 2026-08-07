from __future__ import annotations

import frappe
from frappe.model.document import Document

from hotel_erp.finance import billing
from hotel_erp.hr.staff_assignment import pick_least_loaded_staff

_OPEN_STATUSES = ["open", "assigned", "in_progress"]


class MaintenanceRequest(Document):
    def before_insert(self):
        if not self.opened_at:
            self.opened_at = frappe.utils.now_datetime()

    def after_insert(self):
        if self.technician:
            return
        assignee = pick_least_loaded_staff(
            department="Maintenance",
            open_task_doctype="Maintenance Request",
            assignee_field="technician",
            open_status_field="status",
            open_statuses=_OPEN_STATUSES,
        )
        if assignee:
            frappe.db.set_value("Maintenance Request", self.name, {"technician": assignee, "status": "assigned"})

    def on_update(self):
        """`closed_at` is set explicitly by `api.maintenance.close_request`
        (the final-closure step) -- this only posts the repair-cost expense
        line at that same moment, once, if a cost was entered."""
        before = self.get_doc_before_save()
        if before is None or before.status == self.status:
            return
        if self.status == "closed" and before.status != "closed":
            billing.post_maintenance_expense(self)
