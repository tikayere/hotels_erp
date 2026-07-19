"""Room Type controller.

`code` must be unique PER PROPERTY, not globally (doctype_spec.md §3 naming
note). A Frappe `unique=1` field constraint is global, so the docname uses
`autoname: hash` and per-property uniqueness is enforced here in validate().
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class RoomType(Document):
    def validate(self):
        self._validate_unique_code_per_property()

    def _validate_unique_code_per_property(self):
        existing = frappe.db.get_value(
            "Room Type",
            {"property": self.property, "code": self.code, "name": ["!=", self.name]},
            "name",
        )
        if existing:
            frappe.throw(
                f"Room Type code '{self.code}' already exists for property '{self.property}'",
                frappe.DuplicateEntryError,
            )
