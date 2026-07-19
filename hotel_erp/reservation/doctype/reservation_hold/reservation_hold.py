"""Reservation Hold controller.

Docname is `HOLD-<hash6>` (doctype_spec.md §3). `idempotency_key` is unique per
room_type (composite unique index in the JSON), an inventory-level backstop to
the higher-level @idempotent decorator on the /reservations/hold endpoint.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class ReservationHold(Document):
    def autoname(self):
        self.name = f"HOLD-{frappe.generate_hash(length=6)}"

    def validate(self):
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            frappe.throw("check_out must be after check_in")
        if self.rooms_requested is not None and self.rooms_requested < 1:
            frappe.throw("rooms_requested must be >= 1")
