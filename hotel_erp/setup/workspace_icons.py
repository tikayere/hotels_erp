"""Icons for the Desk left sidebar tree.

Frappe auto-generates a "Workspace Sidebar" doc per public Workspace
(`frappe.desk.doctype.workspace_sidebar.workspace_sidebar.
create_workspace_sidebar_for_workspaces`), building each "Workspace Sidebar
Item" row from `Workspace.shortcuts` -- but that generator never copies
`shortcut.icon` across, so every item lands with `icon = NULL` regardless of
what the Workspace fixture itself specifies. The sidebar then falls back to a
generic "list" icon for literally everything (frappe's own
`sidebar_item.js`), which is why the left nav looked flat/unbranded. This
module is the workaround: it makes sure the sidebar docs exist, then
explicitly sets a real icon per item and per section header, keyed off the
same labels the Workspace fixtures use. Runs once at install (`after_install`)
and once as a migrate-time patch (`patches.txt`) so it also reaches sites
that installed this app before this fix existed.
"""
from __future__ import annotations

import frappe

HEADER_ICONS = {
    "Hotel Management": "house",
    "Front Desk": "users",
    "Housekeeping": "clipboard",
    "Maintenance": "hammer",
    "Revenue Management": "chart-line",
    "Finance": "credit-card",
    "HR": "user-check",
}

ITEM_ICONS = {
    "Property": "building-2",
    "Room Type": "bed-double",
    "Room": "door-closed",
    "Front Desk": "users",
    "Housekeeping": "clipboard",
    "Maintenance": "hammer",
    "Revenue Management": "chart-line",
    "Finance": "credit-card",
    "HR": "user-check",
    "Reservation": "calendar-check",
    "Reservation Hold": "hourglass",
    "Room Assignment": "door-open",
    "Waiting List Entry": "list-plus",
    "Guest": "user-round",
    "Today's Arrivals": "plane-landing",
    "Today's Departures": "plane-takeoff",
    "Late Checkouts": "clock-alert",
    "Arrivals Not Checked In": "user-x",
    "Housekeeping Task": "clipboard-list",
    "Housekeeping Task Board": "kanban",
    "Maintenance Request": "wrench",
    "Maintenance Request Board": "kanban",
    "Rate Plan": "tag",
    "Rate Calendar": "calendar-days",
    "Pricing Rule": "percent",
    "ADR and RevPAR": "trending-up",
    "Hotel Occupancy": "chart-bar",
    "Finance Txn": "receipt",
    "Staff": "users-round",
    "Payroll Entry": "banknote",
    "Leave Application": "calendar-x",
}


def set_sidebar_icons() -> None:
    from frappe.desk.doctype.workspace_sidebar.workspace_sidebar import (
        create_workspace_sidebar_for_workspaces,
    )

    # Idempotent: skips any workspace that already has a Workspace Sidebar doc.
    for sidebar in create_workspace_sidebar_for_workspaces() or []:
        sidebar.insert(ignore_permissions=True)

    for title, header_icon in HEADER_ICONS.items():
        if frappe.db.exists("Workspace Sidebar", title):
            frappe.db.set_value("Workspace Sidebar", title, "header_icon", header_icon)

    items = frappe.get_all(
        "Workspace Sidebar Item",
        filters={"parenttype": "Workspace Sidebar", "parent": ["in", list(HEADER_ICONS)]},
        fields=["name", "parent", "label", "link_type"],
    )
    for item in items:
        icon = ITEM_ICONS.get(item.label)
        if not icon and item.link_type == "Workspace" and item.label == "Home":
            icon = HEADER_ICONS.get(item.parent)
        if icon:
            frappe.db.set_value("Workspace Sidebar Item", item.name, "icon", icon)
