"""Session-authenticated internal API for the Inventory module of the `/pms`
SPA -- stock items, suppliers, purchase orders. Read access is
`pms_common.INVENTORY_READ_ROLES` (Housekeeping Staff + System Manager, the
department that actually draws down linen/cleaning-supply stock day to day
-- see `restaurant/events.py`'s `_consume_stock` for the other consumer, an
automatic hook rather than a person). Every write is System-Manager-only
(`pms_common.INVENTORY_WRITE_ROLES`), matching `Purchase Order` and
`Supplier`'s own DocType permissions, which grant no other role anything --
there's no dedicated purchasing role in this codebase yet.

`mark_received` is the one place this module does more than a plain status
flip: receiving a PO increments each line's `Inventory Item.quantity_on_hand`
-- the restock counterpart to `restaurant.events._consume_stock`'s
decrement, so stock levels reflect both directions of real movement, not
just consumption.
"""
from __future__ import annotations

import json

import frappe

from hotel_erp.api.pms_common import require_inventory_read, require_inventory_write


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_items(category=None, low_stock=None):
    require_inventory_read()
    filters: dict = {}
    if category:
        filters["category"] = category
    rows = frappe.get_all(
        "Inventory Item",
        filters=filters,
        fields=["name", "item_name", "category", "unit", "quantity_on_hand", "reorder_level", "preferred_supplier"],
        order_by="item_name",
    )
    if low_stock and str(low_stock).lower() not in ("0", "false"):
        rows = [r for r in rows if r.reorder_level is not None and (r.quantity_on_hand or 0) <= r.reorder_level]
    return rows


@frappe.whitelist()
def create_item(item_name, category, unit=None, quantity_on_hand=0, reorder_level=None, preferred_supplier=None):
    require_inventory_write()
    doc = frappe.get_doc(
        {
            "doctype": "Inventory Item",
            "item_name": item_name,
            "category": category,
            "unit": unit,
            "quantity_on_hand": quantity_on_hand or 0,
            "reorder_level": reorder_level,
            "preferred_supplier": preferred_supplier or None,
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def update_item(name, quantity_on_hand=None, reorder_level=None, preferred_supplier=None, unit=None):
    """Manual stock-count correction (a physical recount, a shrinkage
    write-off) -- distinct from the automatic in/out movements
    `mark_received`/`restaurant.events._consume_stock` perform, which is why
    this sets `quantity_on_hand` directly rather than taking a delta."""
    require_inventory_write()
    doc = frappe.get_doc("Inventory Item", name)
    if quantity_on_hand is not None:
        doc.quantity_on_hand = quantity_on_hand
    if reorder_level is not None:
        doc.reorder_level = reorder_level
    if preferred_supplier is not None:
        doc.preferred_supplier = preferred_supplier or None
    if unit is not None:
        doc.unit = unit
    doc.save(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_suppliers(active_only=True, category=None):
    require_inventory_read()
    filters: dict = {}
    if active_only and str(active_only).lower() not in ("0", "false"):
        filters["active"] = 1
    if category:
        filters["category"] = category
    return frappe.get_all(
        "Supplier",
        filters=filters,
        fields=["name", "supplier_name", "contact_person", "phone", "email", "category", "active"],
        order_by="supplier_name",
    )


@frappe.whitelist()
def create_supplier(supplier_name, contact_person=None, phone=None, email=None, category=None, active=1):
    require_inventory_write()
    doc = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "contact_person": contact_person,
            "phone": phone,
            "email": email,
            "category": category,
            "active": active,
        }
    ).insert(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Purchase orders
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_purchase_orders(status=None, supplier=None):
    require_inventory_read()
    filters: dict = {}
    if status:
        filters["status"] = status
    if supplier:
        filters["supplier"] = supplier
    return frappe.get_all(
        "Purchase Order",
        filters=filters,
        fields=["name", "supplier", "total_amount_minor", "currency", "status", "ordered_at", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist()
def get_purchase_order(name):
    require_inventory_read()
    doc = frappe.get_doc("Purchase Order", name).as_dict()
    doc["items"] = frappe.parse_json(doc["items"]) if isinstance(doc.get("items"), str) else (doc.get("items") or [])
    return doc


@frappe.whitelist()
def create_purchase_order(supplier, items, total_amount_minor, currency):
    require_inventory_write()
    if not isinstance(items, str):
        items = json.dumps(items)
    doc = frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "supplier": supplier,
            "items": items,
            "total_amount_minor": total_amount_minor,
            "currency": currency,
            "status": "draft",
        }
    ).insert(ignore_permissions=True)
    return get_purchase_order(doc.name)


@frappe.whitelist()
def mark_ordered(name):
    require_inventory_write()
    doc = frappe.get_doc("Purchase Order", name)
    if doc.status != "draft":
        frappe.throw(f"Only a draft order can be marked ordered (current status: {doc.status})")
    doc.status = "ordered"
    doc.ordered_at = frappe.utils.now_datetime()
    doc.save(ignore_permissions=True)
    return get_purchase_order(name)


@frappe.whitelist()
def mark_received(name):
    require_inventory_write()
    doc = frappe.get_doc("Purchase Order", name)
    if doc.status != "ordered":
        frappe.throw(f"Only an ordered order can be marked received (current status: {doc.status})")
    doc.status = "received"
    doc.save(ignore_permissions=True)

    items = frappe.parse_json(doc.items) if isinstance(doc.items, str) else (doc.items or [])
    for line in items:
        item_name = (line or {}).get("item")
        qty = (line or {}).get("qty")
        if not item_name or not qty:
            continue
        inventory_item = frappe.db.get_value("Inventory Item", {"item_name": item_name}, "name")
        if not inventory_item:
            continue
        frappe.db.sql(
            "UPDATE `tabInventory Item` SET quantity_on_hand = quantity_on_hand + %(qty)s WHERE name = %(name)s",
            {"qty": qty, "name": inventory_item},
        )
    return get_purchase_order(name)


@frappe.whitelist()
def cancel_purchase_order(name):
    require_inventory_write()
    doc = frappe.get_doc("Purchase Order", name)
    if doc.status in ("received", "cancelled"):
        frappe.throw(f"A {doc.status} order cannot be cancelled")
    doc.status = "cancelled"
    doc.save(ignore_permissions=True)
    return get_purchase_order(name)
