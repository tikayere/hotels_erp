"""Restaurant Order document-event handlers (registered in hooks.py
doc_events). Two internal-only (FR-A8-A15) workflows, both purely
"build per usual Frappe conventions" scope -- neither crosses the §4.5 API
boundary:

* **Kitchen order routing** -- on transition to `in_kitchen`, auto-assign
  the order to the least-loaded active Restaurant-department Staff member,
  the same round-robin-by-current-load helper Housekeeping uses.
* **Stock consumption** -- on transition to `served`, decrement
  `Inventory Item.quantity_on_hand` for every line in `items` whose `item`
  name exactly matches a real Inventory Item. This is a deliberately
  scoped approximation: there's no recipe/BOM doctype mapping menu items to
  their ingredients, so only line items that themselves happen to name a
  tracked Inventory Item (e.g. a bottled drink sold as-is) are decremented.
  Building full recipe-based consumption is a real feature, not an
  "internal module workflow" gap -- out of scope here.
"""
from __future__ import annotations

import frappe

from hotel_erp.hr.staff_assignment import pick_least_loaded_staff

_OPEN_ORDER_STATUSES = ["placed", "in_kitchen"]


def on_restaurant_order_update(doc, method=None):
    before = doc.get_doc_before_save()
    if before is None or before.status == doc.status:
        return

    if doc.status == "in_kitchen" and not doc.assigned_to:
        _route_to_kitchen(doc)

    if doc.status == "served":
        _consume_stock(doc)


def _route_to_kitchen(doc) -> None:
    assignee = pick_least_loaded_staff(
        department="Restaurant",
        open_task_doctype="Restaurant Order",
        assignee_field="assigned_to",
        open_status_field="status",
        open_statuses=_OPEN_ORDER_STATUSES,
    )
    if assignee:
        frappe.db.set_value("Restaurant Order", doc.name, "assigned_to", assignee)


def _consume_stock(doc) -> None:
    try:
        items = frappe.parse_json(doc.items) if isinstance(doc.items, str) else (doc.items or [])
    except ValueError:
        return

    for line in items:
        item_name = (line or {}).get("item")
        qty = (line or {}).get("qty")
        if not item_name or not qty:
            continue
        inventory_item = frappe.db.get_value("Inventory Item", {"item_name": item_name}, "name")
        if not inventory_item:
            continue
        # GREATEST(0, ...) rather than allowing negative stock -- an order can be
        # served with insufficient recorded stock (e.g. a missed purchase), and
        # this workflow's job is to keep the count informative, not to block
        # service over it.
        frappe.db.sql(
            """
            UPDATE `tabInventory Item`
            SET quantity_on_hand = GREATEST(0, quantity_on_hand - %(qty)s)
            WHERE name = %(name)s
            """,
            {"qty": qty, "name": inventory_item},
        )
