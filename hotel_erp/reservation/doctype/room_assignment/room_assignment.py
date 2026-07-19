"""Room Assignment — internal only, never crosses the API boundary (§4.1
principle 3). Created by the front-desk/housekeeping workflow at or near
check-in. Setting Reservation.status = checked_in requires an assignment to
exist first (enforced in hotel_erp.reservation.events)."""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class RoomAssignment(Document):
    def before_insert(self):
        if not self.assigned_at:
            self.assigned_at = frappe.utils.now_datetime()
