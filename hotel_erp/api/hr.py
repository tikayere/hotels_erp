"""Session-authenticated internal API for the HR module of the `/pms` SPA --
Staff directory, Leave Applications, Payroll. Both reads and writes are
restricted to `pms_common.HR_ROLES`: employment and payroll data is the most
sensitive thing this app stores (see `hotel_erp.hr.payroll`'s own docstring:
the Aggregator contract explicitly excludes payroll from anything it may
ever see), so unlike the operational modules there's no broad staff-read
tier here at all.
"""
from __future__ import annotations

import frappe
from frappe.utils import getdate

from hotel_erp.api.pms_common import require_hr_role

_DEPARTMENTS = ("Front Desk", "Housekeeping", "Maintenance", "Restaurant", "Finance", "HR", "Management")


# ---------------------------------------------------------------------------
# Staff directory
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_staff(department=None, status=None, search=None):
    require_hr_role()
    filters: dict = {}
    if department:
        filters["department"] = department
    if status:
        filters["status"] = status
    if search:
        filters["employee_name"] = ["like", f"%{search}%"]
    return frappe.get_all(
        "Staff",
        filters=filters,
        fields=[
            "name",
            "employee_name",
            "department",
            "designation",
            "phone",
            "email",
            "date_of_joining",
            "status",
            "user",
            "daily_rate_minor",
        ],
        order_by="employee_name",
    )


@frappe.whitelist()
def get_staff(name):
    require_hr_role()
    return frappe.get_doc("Staff", name).as_dict()


@frappe.whitelist()
def create_staff(
    employee_name,
    department,
    designation=None,
    phone=None,
    email=None,
    date_of_joining=None,
    daily_rate_minor=None,
    user=None,
):
    require_hr_role()
    if department not in _DEPARTMENTS:
        frappe.throw(f"department must be one of: {', '.join(_DEPARTMENTS)}")
    doc = frappe.get_doc(
        {
            "doctype": "Staff",
            "employee_name": employee_name,
            "department": department,
            "designation": designation,
            "phone": phone,
            "email": email,
            "date_of_joining": date_of_joining or getdate(),
            "daily_rate_minor": daily_rate_minor,
            "user": user or None,
            "status": "active",
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def update_staff(name, **fields):
    require_hr_role()
    editable = {"status", "department", "designation", "phone", "email", "daily_rate_minor", "user"}
    doc = frappe.get_doc("Staff", name)
    for key, value in fields.items():
        if key in editable:
            setattr(doc, key, value or None)
    doc.save(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Leave applications
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_leave_applications(staff=None, status=None):
    require_hr_role()
    filters: dict = {}
    if staff:
        filters["staff"] = staff
    if status:
        filters["status"] = status
    rows = frappe.get_all(
        "Leave Application",
        filters=filters,
        fields=["name", "staff", "leave_type", "from_date", "to_date", "status", "reason", "creation"],
        order_by="from_date desc",
    )
    if rows:
        names = {r.staff for r in rows}
        staff_names = dict(
            frappe.get_all("Staff", filters={"name": ["in", list(names)]}, fields=["name", "employee_name"], as_list=True)
        )
        for r in rows:
            r["staff_name"] = staff_names.get(r.staff, r.staff)
    return rows


@frappe.whitelist()
def create_leave_application(staff, leave_type, from_date, to_date, reason=None):
    require_hr_role()
    doc = frappe.get_doc(
        {
            "doctype": "Leave Application",
            "staff": staff,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "reason": reason,
            "status": "pending",
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def approve_leave(name):
    require_hr_role()
    doc = frappe.get_doc("Leave Application", name)
    if doc.status != "pending":
        frappe.throw(f"Only a pending application can be approved (current status: {doc.status})")
    doc.status = "approved"
    doc.save(ignore_permissions=True)

    today = getdate()
    if getdate(doc.from_date) <= today <= getdate(doc.to_date):
        frappe.db.set_value("Staff", doc.staff, "status", "on_leave")
    return doc.as_dict()


@frappe.whitelist()
def reject_leave(name, reason=None):
    require_hr_role()
    doc = frappe.get_doc("Leave Application", name)
    if doc.status != "pending":
        frappe.throw(f"Only a pending application can be rejected (current status: {doc.status})")
    doc.status = "rejected"
    doc.save(ignore_permissions=True)
    if reason:
        doc.add_comment("Comment", f"Rejected: {reason}")
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_payroll_entries(staff=None, status=None, pay_period_start=None, pay_period_end=None):
    require_hr_role()
    filters: dict = {}
    if staff:
        filters["staff"] = staff
    if status:
        filters["status"] = status
    if pay_period_start:
        filters["pay_period_start"] = pay_period_start
    if pay_period_end:
        filters["pay_period_end"] = pay_period_end
    rows = frappe.get_all(
        "Payroll Entry",
        filters=filters,
        fields=[
            "name",
            "staff",
            "pay_period_start",
            "pay_period_end",
            "gross_amount_minor",
            "deductions_minor",
            "net_amount_minor",
            "currency",
            "status",
        ],
        order_by="pay_period_start desc",
    )
    if rows:
        names = {r.staff for r in rows}
        staff_names = dict(
            frappe.get_all("Staff", filters={"name": ["in", list(names)]}, fields=["name", "employee_name"], as_list=True)
        )
        for r in rows:
            r["staff_name"] = staff_names.get(r.staff, r.staff)
    return rows


@frappe.whitelist()
def get_payroll_entry(name):
    require_hr_role()
    return frappe.get_doc("Payroll Entry", name).as_dict()


@frappe.whitelist()
def generate_payroll(pay_period_start, pay_period_end, currency, deduction_rate=0.10):
    """Thin, role-gated wrapper over `hotel_erp.hr.payroll.
    generate_payroll_entries` -- that function is whitelisted for bench
    console use and enforces no permissions of its own, so this is what
    actually authorizes the SPA's "Run Payroll" button."""
    require_hr_role()
    from hotel_erp.hr.payroll import generate_payroll_entries

    created = generate_payroll_entries(
        pay_period_start, pay_period_end, currency, deduction_rate=float(deduction_rate)
    )
    return {"created": created, "count": len(created)}


@frappe.whitelist()
def process_payroll(name):
    require_hr_role()
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.status != "draft":
        frappe.throw(f"Only a draft entry can be processed (current status: {doc.status})")
    doc.status = "processed"
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def pay_payroll(name):
    require_hr_role()
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.status != "processed":
        frappe.throw(f"Only a processed entry can be marked paid (current status: {doc.status})")
    doc.status = "paid"
    doc.save(ignore_permissions=True)
    return doc.as_dict()
