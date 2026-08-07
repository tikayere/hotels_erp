"""Session-authenticated internal API for the Conference module of the
`/pms` SPA -- booking a meeting/event space. Restricted throughout to
`pms_common.CONFERENCE_ROLES` (Hotel Front Desk + System Manager), matching
`Conference Booking`'s own DocType permissions.

`space_name`/`booked_by` are plain Data fields, not Links (there's no
"Meeting Space" or separate booking-contact DocType in this codebase) -- the
SPA free-types both rather than offering a picker backed by data that
doesn't exist yet.
"""
from __future__ import annotations

import frappe

from hotel_erp.api.pms_common import require_conference_role


@frappe.whitelist()
def list_bookings(status=None, from_date=None, to_date=None):
    require_conference_role()
    conditions = ["1=1"]
    values: dict = {}
    if status:
        conditions.append("status = %(status)s")
        values["status"] = status
    if from_date:
        conditions.append("DATE(end_at) >= %(from_date)s")
        values["from_date"] = from_date
    if to_date:
        conditions.append("DATE(start_at) <= %(to_date)s")
        values["to_date"] = to_date

    return frappe.db.sql(
        f"""
        SELECT name, space_name, booked_by, start_at, end_at, catering, status,
               total_amount_minor, currency
        FROM `tabConference Booking`
        WHERE {" AND ".join(conditions)}
        ORDER BY start_at
        """,
        values,
        as_dict=True,
    )


@frappe.whitelist()
def get_booking(name):
    require_conference_role()
    doc = frappe.get_doc("Conference Booking", name).as_dict()
    doc["catering"] = frappe.parse_json(doc["catering"]) if isinstance(doc.get("catering"), str) else doc.get("catering")
    return doc


@frappe.whitelist()
def create_booking(space_name, booked_by, start_at, end_at, catering=None, total_amount_minor=None, currency=None):
    require_conference_role()
    # The doctype's own `validate()` also blocks an overlapping booking (so
    # Desk-created bookings are protected too); this SQL check runs first so
    # the SPA gets the friendlier "which booking conflicts" message before
    # `insert()` even attempts to save.
    overlap = frappe.db.sql(
        """
        SELECT name FROM `tabConference Booking`
        WHERE space_name = %(space_name)s AND status != 'cancelled'
          AND start_at < %(end_at)s AND end_at > %(start_at)s
        LIMIT 1
        """,
        {"space_name": space_name, "start_at": start_at, "end_at": end_at},
    )
    if overlap:
        frappe.throw(f"{space_name} is already booked over part of that window ({overlap[0][0]})")

    doc = frappe.get_doc(
        {
            "doctype": "Conference Booking",
            "space_name": space_name,
            "booked_by": booked_by,
            "start_at": start_at,
            "end_at": end_at,
            "catering": catering,
            "total_amount_minor": total_amount_minor or None,
            "currency": currency,
            "status": "tentative",
        }
    ).insert(ignore_permissions=True)
    return get_booking(doc.name)


@frappe.whitelist()
def confirm_booking(name):
    require_conference_role()
    doc = frappe.get_doc("Conference Booking", name)
    if doc.status != "tentative":
        frappe.throw(f"Only a tentative booking can be confirmed (current status: {doc.status})")
    doc.status = "confirmed"
    doc.save(ignore_permissions=True)
    return get_booking(name)


@frappe.whitelist()
def complete_booking(name):
    require_conference_role()
    doc = frappe.get_doc("Conference Booking", name)
    if doc.status != "confirmed":
        frappe.throw(f"Only a confirmed booking can be marked completed (current status: {doc.status})")
    doc.status = "completed"
    doc.save(ignore_permissions=True)
    return get_booking(name)


@frappe.whitelist()
def cancel_booking(name):
    require_conference_role()
    doc = frappe.get_doc("Conference Booking", name)
    if doc.status == "cancelled":
        frappe.throw("This booking is already cancelled")
    doc.status = "cancelled"
    doc.save(ignore_permissions=True)
    return get_booking(name)
