from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date

from hotel_erp.hr.staff_assignment import pick_least_loaded_staff

# Response-time SLA, matched to priority -- these are internal targets (no
# guest-facing wire contract for complaints), chosen to be plausible for a
# small/mid property: an urgent complaint (e.g. no hot water) gets a couple
# of hours' response target, a low-priority one a few days.
_SLA_HOURS = {"urgent": 2, "high": 8, "medium": 24, "low": 72}

# Which department is best placed to actually resolve a given category --
# not every category maps to an obvious department, so anything not listed
# here (service/other) routes to Front Desk, who can always triage further.
_CATEGORY_DEPARTMENT = {
    "room": "Housekeeping",
    "cleanliness": "Housekeeping",
    "noise": "Housekeeping",
    "billing": "Finance",
}
_DEFAULT_DEPARTMENT = "Front Desk"

_OPEN_STATUSES = ["open", "in_progress", "escalated"]


class GuestComplaint(Document):
    def before_insert(self):
        if not self.raised_at:
            self.raised_at = frappe.utils.now_datetime()
        if not self.due_by:
            hours = _SLA_HOURS.get(self.priority or "medium", _SLA_HOURS["medium"])
            self.due_by = add_to_date(self.raised_at, hours=hours)

    def after_insert(self):
        if self.assigned_to:
            return
        department = _CATEGORY_DEPARTMENT.get(self.category, _DEFAULT_DEPARTMENT)
        assignee = pick_least_loaded_staff(
            department=department,
            open_task_doctype="Guest Complaint",
            assignee_field="assigned_to",
            open_status_field="status",
            open_statuses=_OPEN_STATUSES,
        )
        if assignee:
            frappe.db.set_value("Guest Complaint", self.name, "assigned_to", assignee)
