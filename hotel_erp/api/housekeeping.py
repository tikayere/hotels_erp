"""Session-authenticated internal API for the Housekeeping module of the
`/pms` SPA (see `hotel_erp.api.pms`'s module docstring for the general
session-auth / bare-docname contract every `hotel_erp.api.*` internal module
follows).

Reads are open to any staff role (`pms_common.STAFF_ROLES`) -- a Housekeeping
Task's status is exactly what tells Front Desk whether a room is ready to
sell, so every role that touches the room board benefits from seeing it.
Writes (create/assign/start/complete/verify) are restricted to
`pms_common.HOUSEKEEPING_ROLES`, mirroring `Housekeeping Task`'s own DocType
permissions.

`complete_task`/`verify_task` advance the *room's* status too (not just the
task's) -- `cleaning`/`deep_clean` tasks are the ones that actually make a
room sellable again, following the same dirty -> clean -> available pipeline
`housekeeping.auto_assign.create_checkout_task` already puts a room into on
checkout. Other task types (`inspection`, `turndown`, `laundry`) don't touch
room status; they're not what determines sellability.
"""
from __future__ import annotations

import frappe

from hotel_erp.api.pms_common import require_housekeeping_role, require_staff

_ROOM_STATUS_TASK_TYPES = ("cleaning", "deep_clean")


@frappe.whitelist()
def list_tasks(property=None, status=None, room=None, assigned_to=None, mine=False):
    require_staff()
    conditions = ["1=1"]
    values: dict = {}
    if status:
        conditions.append("t.status = %(status)s")
        values["status"] = status
    if room:
        conditions.append("t.room = %(room)s")
        values["room"] = room
    if property:
        conditions.append("rm.property = %(property)s")
        values["property"] = property
    if assigned_to:
        conditions.append("t.assigned_to = %(assigned_to)s")
        values["assigned_to"] = assigned_to
    if mine and str(mine).lower() not in ("0", "false"):
        conditions.append("t.assigned_to = %(me)s")
        values["me"] = frappe.session.user

    return frappe.db.sql(
        f"""
        SELECT t.name, t.room, rm.room_number, rm.floor, rm.property, t.type,
               t.status, t.assigned_to, t.due_at, t.notes
        FROM `tabHousekeeping Task` t
        LEFT JOIN `tabRoom` rm ON rm.name = t.room
        WHERE {" AND ".join(conditions)}
        ORDER BY FIELD(t.status, 'pending', 'in_progress', 'completed', 'verified'), t.due_at
        """,
        values,
        as_dict=True,
    )


@frappe.whitelist()
def get_task(name):
    require_staff()
    task = frappe.get_doc("Housekeeping Task", name)
    room = frappe.db.get_value("Room", task.room, ["room_number", "floor", "property"], as_dict=True)
    out = task.as_dict()
    out["room_number"] = room.room_number if room else None
    out["floor"] = room.floor if room else None
    out["property"] = room.property if room else None
    return out


@frappe.whitelist()
def create_task(room, type, assigned_to=None, due_at=None, notes=None):
    require_housekeeping_role()
    task = frappe.get_doc(
        {
            "doctype": "Housekeeping Task",
            "room": room,
            "type": type,
            "status": "pending",
            "assigned_to": assigned_to or None,
            "due_at": due_at or frappe.utils.now_datetime(),
            "notes": notes,
        }
    ).insert(ignore_permissions=True)
    return get_task(task.name)


@frappe.whitelist()
def assign_task(name, assigned_to):
    require_housekeeping_role()
    frappe.db.set_value("Housekeeping Task", name, "assigned_to", assigned_to)
    return get_task(name)


@frappe.whitelist()
def start_task(name):
    require_housekeeping_role()
    task = frappe.get_doc("Housekeeping Task", name)
    if task.status != "pending":
        frappe.throw(f"Only a pending task can be started (current status: {task.status})")
    task.status = "in_progress"
    task.save(ignore_permissions=True)
    return get_task(name)


@frappe.whitelist()
def complete_task(name):
    require_housekeeping_role()
    task = frappe.get_doc("Housekeeping Task", name)
    if task.status not in ("pending", "in_progress"):
        frappe.throw(f"A {task.status} task cannot be marked completed")
    task.status = "completed"
    task.save(ignore_permissions=True)
    if task.type in _ROOM_STATUS_TASK_TYPES:
        frappe.db.set_value("Room", task.room, "status", "clean")
    return get_task(name)


@frappe.whitelist()
def verify_task(name):
    """A supervisor's final sign-off -- the point a room actually becomes
    bookable again, distinct from housekeeping merely finishing the clean."""
    require_housekeeping_role()
    task = frappe.get_doc("Housekeeping Task", name)
    if task.status != "completed":
        frappe.throw("Only a completed task can be verified")
    task.status = "verified"
    task.save(ignore_permissions=True)
    if task.type in _ROOM_STATUS_TASK_TYPES:
        frappe.db.set_value("Room", task.room, "status", "available")
    return get_task(name)
