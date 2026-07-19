"""Reservation controller.

Docname is a `RES-#####` naming series. `confirmation_number` is derived in
before_insert as `{property_abbr}-{numeric_suffix}` (e.g. SH-1042), matching the
contract's Reservation example (doctype_spec.md §3). guests must have >= 1 row.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class Reservation(Document):
    def before_insert(self):
        # Ensure the naming-series name exists before we derive the confirmation
        # number from its numeric suffix (set_new_name normally runs *after*
        # before_insert; calling it here sets the flag so the framework skips it).
        if not self.name:
            from frappe.model.naming import set_new_name

            set_new_name(self)
        if not self.confirmation_number:
            suffix = self.name.split("-")[-1]
            self.confirmation_number = f"{self._property_abbr()}-{suffix}"

    def validate(self):
        if not self.guests:
            frappe.throw("A reservation requires at least one guest")

    def _property_abbr(self) -> str:
        property_name = frappe.db.get_value(
            "Property",
            frappe.db.get_value("Room Type", self.room_type, "property"),
            "property_name",
        )
        if property_name:
            abbr = "".join(word[0] for word in property_name.split() if word)[:3].upper()
            if abbr:
                return abbr
        return "RES"
