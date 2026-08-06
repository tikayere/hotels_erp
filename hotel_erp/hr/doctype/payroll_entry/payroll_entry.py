"""Payroll Entry controller.

`net_amount_minor` is always derived, never hand-typed: a manually-created
entry (Desk UI) and a `hotel_erp.hr.payroll.generate_payroll_entries` entry
must be equally consistent, so the derivation lives here rather than only in
the generator.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PayrollEntry(Document):
    def validate(self):
        if self.pay_period_end and self.pay_period_start and self.pay_period_end < self.pay_period_start:
            frappe.throw("pay_period_end must be on or after pay_period_start")
        gross = self.gross_amount_minor or 0
        deductions = self.deductions_minor or 0
        if deductions > gross:
            frappe.throw("deductions_minor cannot exceed gross_amount_minor")
        self.net_amount_minor = gross - deductions
