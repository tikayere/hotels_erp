"""Rate Plan controller.

`code` is unique PER ROOM TYPE, not globally (same pattern as Room Type,
doctype_spec.md §3). Enforced in validate() rather than a global `unique=1`.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class RatePlan(Document):
    def validate(self):
        self._validate_unique_code_per_room_type()

    def _validate_unique_code_per_room_type(self):
        existing = frappe.db.get_value(
            "Rate Plan",
            {"room_type": self.room_type, "code": self.code, "name": ["!=", self.name]},
            "name",
        )
        if existing:
            frappe.throw(
                f"Rate Plan code '{self.code}' already exists for room type '{self.room_type}'",
                frappe.DuplicateEntryError,
            )
