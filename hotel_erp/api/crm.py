"""Session-authenticated internal API for the CRM module of the `/pms` SPA --
Guest lookup, Guest Communications (logged calls/emails/texts), Guest
Complaints. Restricted throughout to `pms_common.CRM_ROLES` (Hotel Front
Desk + System Manager), matching `Guest Communication`/`Guest Complaint`'s
own DocType permissions -- guest contact history isn't broad-staff-readable
the way a room or task status is.

Note `Guest` here is the standalone `Guest` DocType (loyalty/VIP profile,
looked up across stays), not the `Reservation Guest` child table
`hotel_erp.api.pms.get_reservation` returns -- the latter is just the
name/phone/email captured on one specific booking and isn't linked to this
DocType at all in this codebase.
"""
from __future__ import annotations

import frappe

from hotel_erp.api.pms_common import require_crm_role


@frappe.whitelist()
def search_guests(search=None):
    require_crm_role()
    filters = {}
    if search:
        filters["guest_name"] = ["like", f"%{search}%"]
    return frappe.get_all(
        "Guest",
        filters=filters,
        fields=["name", "guest_name", "phone", "email", "vip_status", "loyalty_points"],
        order_by="guest_name",
        limit_page_length=50,
    )


@frappe.whitelist()
def get_guest(name):
    require_crm_role()
    guest = frappe.get_doc("Guest", name).as_dict()
    guest["communications"] = frappe.get_all(
        "Guest Communication",
        filters={"guest": name},
        fields=["name", "channel", "direction", "subject", "message", "sent_at"],
        order_by="sent_at desc",
        limit_page_length=20,
    )
    guest["complaints"] = frappe.get_all(
        "Guest Complaint",
        filters={"guest": name},
        fields=["name", "reservation", "category", "description", "status", "priority", "assigned_to", "due_by", "raised_at"],
        order_by="raised_at desc",
        limit_page_length=20,
    )
    return guest


# ---------------------------------------------------------------------------
# Communications
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_communications(guest=None, channel=None):
    require_crm_role()
    filters: dict = {}
    if guest:
        filters["guest"] = guest
    if channel:
        filters["channel"] = channel
    return frappe.get_all(
        "Guest Communication",
        filters=filters,
        fields=["name", "guest", "channel", "direction", "subject", "message", "sent_at"],
        order_by="sent_at desc",
        limit_page_length=100,
    )


@frappe.whitelist()
def create_communication(guest, channel, direction, subject=None, message=None):
    require_crm_role()
    doc = frappe.get_doc(
        {
            "doctype": "Guest Communication",
            "guest": guest,
            "channel": channel,
            "direction": direction,
            "subject": subject,
            "message": message,
            "sent_at": frappe.utils.now_datetime(),
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------
_PRIORITY_SORT_WEIGHT = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


@frappe.whitelist()
def list_complaints(status=None, guest=None, reservation=None):
    require_crm_role()
    filters: dict = {}
    if status:
        filters["status"] = status
    if guest:
        filters["guest"] = guest
    if reservation:
        filters["reservation"] = reservation
    # frappe.get_all's order_by validator only allows plain `field`/`link.field`
    # forms (SQL-injection guard), so a raw FIELD(priority, ...) SQL function is
    # rejected outright -- sort by priority in Python instead.
    rows = frappe.get_all(
        "Guest Complaint",
        filters=filters,
        fields=[
            "name", "guest", "reservation", "category", "description", "status",
            "priority", "assigned_to", "due_by", "raised_at",
        ],
        order_by="raised_at desc",
    )
    # DB already ordered by raised_at desc; a stable sort on priority weight
    # alone preserves that as the secondary/tie-break order.
    rows.sort(key=lambda r: _PRIORITY_SORT_WEIGHT.get(r.priority, 99))
    return rows


@frappe.whitelist()
def get_complaint(name):
    require_crm_role()
    return frappe.get_doc("Guest Complaint", name).as_dict()


@frappe.whitelist()
def create_complaint(guest, description, category=None, reservation=None, priority="medium"):
    require_crm_role()
    doc = frappe.get_doc(
        {
            "doctype": "Guest Complaint",
            "guest": guest,
            "reservation": reservation or None,
            "category": category,
            "description": description,
            "status": "open",
            "priority": priority,
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def update_complaint_status(name, status, resolution=None):
    require_crm_role()
    doc = frappe.get_doc("Guest Complaint", name)
    if status == "resolved" and not (resolution or doc.resolution):
        frappe.throw("A resolution note is required to resolve a complaint")
    doc.status = status
    if resolution:
        doc.resolution = resolution
    doc.save(ignore_permissions=True)
    return doc.as_dict()
