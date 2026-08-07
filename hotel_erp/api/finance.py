"""Session-authenticated internal API for the Finance module of the `/pms`
SPA. Unlike the operational modules (housekeeping/maintenance/restaurant),
both reads and writes here are restricted to `pms_common.FINANCE_ROLES` --
transaction amounts aren't the kind of thing every staff role should be able
to browse, unlike a room or task's status.

`Finance Txn` is a submittable DocType (`is_submittable: 1`): a txn is
created as a draft (`docstatus 0`), reviewed, then submitted (`docstatus 1`,
locked against further field edits by Frappe's own submit semantics) or
cancelled (`docstatus 2`) -- the SPA surfaces that as an explicit two-step
create-then-submit rather than auto-submitting on create, so a mis-entered
amount can still be caught/deleted before it becomes a permanent ledger row.
"""
from __future__ import annotations

import frappe
from frappe.utils import getdate

from hotel_erp.api.pms_common import FOLIO_ROLES, require_finance_role
from hotel_erp.finance import billing

_TYPES = ("revenue", "refund", "tax", "expense", "payment")


def _require_folio_role() -> None:
    if frappe.session.user in ("", "Guest"):
        frappe.throw("Authentication required", frappe.AuthenticationError)
    if not set(frappe.get_roles(frappe.session.user)) & set(FOLIO_ROLES):
        frappe.throw(f"Requires one of: {', '.join(FOLIO_ROLES)}", frappe.PermissionError)


@frappe.whitelist()
def list_txns(type=None, docstatus=None, from_date=None, to_date=None, page=1, page_length=20):
    require_finance_role()
    page = max(1, int(page or 1))
    page_length = min(100, max(1, int(page_length or 20)))

    filters: dict = {}
    if type:
        filters["type"] = type
    if docstatus is not None and docstatus != "":
        filters["docstatus"] = int(docstatus)
    if from_date:
        filters.setdefault("creation", ["between", [getdate(from_date), getdate(to_date or from_date)]])

    total_count = frappe.db.count("Finance Txn", filters)
    rows = frappe.get_all(
        "Finance Txn",
        filters=filters,
        fields=["name", "type", "amount_minor", "currency", "ref", "docstatus", "creation"],
        order_by="creation desc",
        limit_page_length=page_length,
        limit_start=(page - 1) * page_length,
    )
    return {"data": rows, "total_count": total_count, "page": page, "page_length": page_length}


@frappe.whitelist()
def get_txn(name):
    require_finance_role()
    return frappe.get_doc("Finance Txn", name).as_dict()


@frappe.whitelist()
def create_txn(type, amount_minor, currency, ref=None, reservation=None):
    require_finance_role()
    if type not in _TYPES:
        frappe.throw(f"type must be one of: {', '.join(_TYPES)}")
    doc = frappe.get_doc(
        {
            "doctype": "Finance Txn",
            "type": type,
            "amount_minor": amount_minor,
            "currency": currency,
            "ref": ref or reservation,
            "reservation": reservation,
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def submit_txn(name):
    require_finance_role()
    doc = frappe.get_doc("Finance Txn", name)
    if doc.docstatus != 0:
        frappe.throw("Only a draft transaction can be submitted")
    doc.submit()
    return doc.as_dict()


@frappe.whitelist()
def cancel_txn(name):
    require_finance_role()
    doc = frappe.get_doc("Finance Txn", name)
    if doc.docstatus != 1:
        frappe.throw("Only a submitted transaction can be cancelled")
    doc.cancel()
    return doc.as_dict()


@frappe.whitelist()
def get_summary(from_date=None, to_date=None):
    """Submitted-only (`docstatus = 1`) totals by type, for a Finance
    dashboard KPI strip -- drafts and cancelled rows aren't real ledger
    entries yet/anymore, so they're excluded rather than netted in."""
    require_finance_role()
    conditions = ["docstatus = 1"]
    values: dict = {}
    if from_date:
        conditions.append("DATE(creation) >= %(from_date)s")
        values["from_date"] = getdate(from_date)
    if to_date:
        conditions.append("DATE(creation) <= %(to_date)s")
        values["to_date"] = getdate(to_date)

    rows = frappe.db.sql(
        f"""
        SELECT type, SUM(amount_minor) AS total_minor, currency, COUNT(name) AS count
        FROM `tabFinance Txn`
        WHERE {" AND ".join(conditions)}
        GROUP BY type, currency
        """,
        values,
        as_dict=True,
    )
    by_type = {t: {"total_minor": 0, "count": 0, "currency": None} for t in _TYPES}
    for r in rows:
        entry = by_type.setdefault(r.type, {"total_minor": 0, "count": 0, "currency": None})
        entry["total_minor"] += r.total_minor or 0
        entry["count"] += r.count
        entry["currency"] = entry["currency"] or r.currency

    net_minor = (
        by_type["revenue"]["total_minor"]
        - by_type["refund"]["total_minor"]
        - by_type["expense"]["total_minor"]
    )
    return {"by_type": by_type, "net_minor": net_minor}


@frappe.whitelist()
def get_folio(reservation):
    """Itemized guest folio for one reservation -- charges, payments, and
    the computed balance due. Readable by front desk too (not just Finance
    roles): checkout is when this actually gets used, and front desk is who
    stands at the desk when a guest is checking out. See finance/billing.py."""
    _require_folio_role()
    if not frappe.db.exists("Reservation", reservation):
        frappe.throw("Unknown reservation")
    return billing.get_folio(reservation)


@frappe.whitelist()
def record_payment(reservation, amount_minor, currency, method):
    """Records a manual/offline payment (cash/mobile money/bank transfer/
    card) against a reservation's folio. No payment-gateway integration --
    see ENTERPRISE_READINESS_PLAN.md Wave A for why that's deliberate."""
    _require_folio_role()
    name = billing.record_payment(reservation, amount_minor, currency, method)
    return frappe.get_doc("Finance Txn", name).as_dict()
