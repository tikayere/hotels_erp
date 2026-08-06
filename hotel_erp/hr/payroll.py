"""Payroll calculation (FR-A8-A15 internal workflow).

`generate_payroll_entries` is a whitelisted Desk-callable method (bench
console or a future report/button), not part of the §4.5 external contract
-- payroll is explicitly listed as data the Aggregator must never see
(phase_1.md's ecosystem note: "It does NOT store ... Payroll").

Gross pay is `daily_rate_minor * days_in_period` (inclusive of both
endpoints) -- a flat day-rate, not an hours/attendance-based calculation,
since there's no Attendance/timesheet doctype in this codebase to derive
hours worked from. Deductions are a flat `deduction_rate` (default 10%,
a placeholder for real tax/benefits withholding rules, which are a
jurisdiction-specific feature well beyond "internal module workflow"
scope). Idempotent per (staff, pay_period_start, pay_period_end): re-running
for a period that already has an entry for a given staff member skips them
rather than creating a duplicate.
"""
from __future__ import annotations

import frappe


@frappe.whitelist()
def generate_payroll_entries(
    pay_period_start,
    pay_period_end,
    currency,
    deduction_rate: float = 0.10,
) -> list[str]:
    start = frappe.utils.getdate(pay_period_start)
    end = frappe.utils.getdate(pay_period_end)
    if end < start:
        frappe.throw("pay_period_end must be on or after pay_period_start")
    days = (end - start).days + 1

    created: list[str] = []
    staff = frappe.get_all(
        "Staff",
        filters={"status": "active", "daily_rate_minor": [">", 0]},
        fields=["name", "daily_rate_minor"],
    )
    for s in staff:
        if frappe.db.exists(
            "Payroll Entry",
            {"staff": s.name, "pay_period_start": start, "pay_period_end": end},
        ):
            continue

        gross = int(s.daily_rate_minor) * days
        deductions = round(gross * deduction_rate)

        entry = frappe.get_doc(
            {
                "doctype": "Payroll Entry",
                "staff": s.name,
                "pay_period_start": start,
                "pay_period_end": end,
                "gross_amount_minor": gross,
                "deductions_minor": deductions,
                "currency": currency,
                "status": "draft",
            }
        ).insert(ignore_permissions=True)
        created.append(entry.name)

    return created
