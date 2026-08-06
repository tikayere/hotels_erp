"""Session-authenticated internal API for the Maintenance module of the
`/pms` SPA -- see `hotel_erp.api.housekeeping`'s module docstring for the
same read-broad/write-narrow reasoning (a maintenance issue on a room is
exactly as relevant to Front Desk's sellability picture as a housekeeping
task is).

`create_request` and `resolve_request` also update the linked Room's status,
same spirit as `housekeeping.auto_assign.create_checkout_task`: a room with
an *open, urgent* issue shouldn't be sellable, and a *resolved* one should go
back through housekeeping (not straight to available) before it's sold
again -- deliberately conservative, matching how `checked_out` already routes
through `dirty` rather than `available`. Both only ever touch a room that
isn't currently `occupied` -- a guest staying through a minor maintenance fix
(e.g. a slow drain) is common and must not get bounced out of inventory.
"""
from __future__ import annotations

import frappe

from hotel_erp.api.pms_common import require_maintenance_role, require_staff

_OPEN_STATUSES = ("open", "assigned", "in_progress")


@frappe.whitelist()
def list_requests(property=None, status=None, priority=None, room=None):
    require_staff()
    conditions = ["1=1"]
    values: dict = {}
    if status:
        conditions.append("m.status = %(status)s")
        values["status"] = status
    if priority:
        conditions.append("m.priority = %(priority)s")
        values["priority"] = priority
    if room:
        conditions.append("m.room = %(room)s")
        values["room"] = room
    if property:
        conditions.append("rm.property = %(property)s")
        values["property"] = property

    return frappe.db.sql(
        f"""
        SELECT m.name, m.room, rm.room_number, rm.floor, rm.property, m.issue,
               m.status, m.priority, m.technician, m.opened_at, m.closed_at
        FROM `tabMaintenance Request` m
        LEFT JOIN `tabRoom` rm ON rm.name = m.room
        WHERE {" AND ".join(conditions)}
        ORDER BY FIELD(m.priority, 'urgent', 'high', 'medium', 'low'), m.opened_at
        """,
        values,
        as_dict=True,
    )


@frappe.whitelist()
def get_request(name):
    require_staff()
    req = frappe.get_doc("Maintenance Request", name)
    out = req.as_dict()
    if req.room:
        room = frappe.db.get_value("Room", req.room, ["room_number", "floor", "property"], as_dict=True)
        out["room_number"] = room.room_number if room else None
        out["floor"] = room.floor if room else None
        out["property"] = room.property if room else None
    return out


@frappe.whitelist()
def create_request(issue, room=None, priority="medium"):
    require_maintenance_role()
    req = frappe.get_doc(
        {
            "doctype": "Maintenance Request",
            "room": room or None,
            "issue": issue,
            "priority": priority,
            "status": "open",
        }
    ).insert(ignore_permissions=True)

    if room:
        room_status = frappe.db.get_value("Room", room, "status")
        if room_status != "occupied":
            frappe.db.set_value(
                "Room", room, "status", "out_of_order" if priority == "urgent" else "maintenance"
            )
    return get_request(req.name)


@frappe.whitelist()
def assign_request(name, technician):
    require_maintenance_role()
    req = frappe.get_doc("Maintenance Request", name)
    req.technician = technician
    if req.status == "open":
        req.status = "assigned"
    req.save(ignore_permissions=True)
    return get_request(name)


@frappe.whitelist()
def start_request(name):
    require_maintenance_role()
    req = frappe.get_doc("Maintenance Request", name)
    if req.status not in ("open", "assigned"):
        frappe.throw(f"Only an open or assigned request can be started (current status: {req.status})")
    req.status = "in_progress"
    req.save(ignore_permissions=True)
    return get_request(name)


@frappe.whitelist()
def resolve_request(name):
    require_maintenance_role()
    req = frappe.get_doc("Maintenance Request", name)
    if req.status not in _OPEN_STATUSES:
        frappe.throw(f"A {req.status} request cannot be resolved")
    req.status = "resolved"
    req.save(ignore_permissions=True)

    if req.room:
        room_status = frappe.db.get_value("Room", req.room, "status")
        if room_status in ("maintenance", "out_of_order"):
            frappe.db.set_value("Room", req.room, "status", "dirty")
    return get_request(name)


@frappe.whitelist()
def close_request(name):
    require_maintenance_role()
    req = frappe.get_doc("Maintenance Request", name)
    if req.status != "resolved":
        frappe.throw("Only a resolved request can be closed")
    req.status = "closed"
    req.closed_at = frappe.utils.now_datetime()
    req.save(ignore_permissions=True)
    return get_request(name)
