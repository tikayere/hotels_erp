"""Session-authenticated internal API for the Restaurant module of the `/pms`
SPA. Reads are staff-broad, writes restricted to `pms_common.RESTAURANT_ROLES`
(Hotel Front Desk + System Manager) -- this codebase has no separate
kitchen/waitstaff role yet, orders are entered and tracked by Front Desk on
the guest's behalf (see `restaurant/events.py`'s own docstring, which
auto-assigns to whichever Staff row is in the "Restaurant" department once an
order is sent to the kitchen -- that's a `Staff`/`User` link, not a login
role, so it doesn't need its own SPA-visible role tier).

Status transitions here are intentionally thin: `restaurant.events.
on_restaurant_order_update` (a `doc_events` hook, not called directly by
this module) is what actually does the kitchen-routing and stock-consumption
side effects the moment `.save()` changes `status` -- these functions just
perform the transition and let that hook fire.
"""
from __future__ import annotations

import json

import frappe

from hotel_erp.api.pms_common import require_restaurant_role, require_staff

_STATUS_FLOW = {
    "placed": "in_kitchen",
    "in_kitchen": "served",
    "served": "billed",
}


@frappe.whitelist()
def list_orders(status=None, reservation=None):
    require_staff()
    filters: dict = {}
    if status:
        filters["status"] = status
    if reservation:
        filters["reservation"] = reservation
    return frappe.get_all(
        "Restaurant Order",
        filters=filters,
        fields=["name", "reservation", "assigned_to", "amount_minor", "currency", "status", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist()
def get_order(name):
    require_staff()
    order = frappe.get_doc("Restaurant Order", name)
    out = order.as_dict()
    out["items"] = frappe.parse_json(order.items) if isinstance(order.items, str) else (order.items or [])
    return out


@frappe.whitelist()
def create_order(items, amount_minor, currency, reservation=None):
    """`items` is a JSON string (or list) of `{item, qty, price_minor}` lines
    -- the SPA computes `amount_minor` client-side from those lines and sends
    both rather than this endpoint re-deriving it, so a discount or
    ad-hoc line the form doesn't model yet isn't silently overridden."""
    require_restaurant_role()
    if not isinstance(items, str):
        items = json.dumps(items)
    order = frappe.get_doc(
        {
            "doctype": "Restaurant Order",
            "reservation": reservation or None,
            "items": items,
            "amount_minor": amount_minor,
            "currency": currency,
            "status": "placed",
        }
    ).insert(ignore_permissions=True)
    return get_order(order.name)


@frappe.whitelist()
def advance_order(name):
    """Move an order to the next step of `placed -> in_kitchen -> served ->
    billed`. A dedicated "next status" action rather than a generic
    `set_status(name, status)` because the flow only ever moves forward one
    step at a time from this screen -- skipping straight from `placed` to
    `served` isn't a real front-desk action."""
    require_restaurant_role()
    order = frappe.get_doc("Restaurant Order", name)
    next_status = _STATUS_FLOW.get(order.status)
    if not next_status:
        frappe.throw(f"A {order.status} order has no further forward step")
    order.status = next_status
    order.save(ignore_permissions=True)  # on_restaurant_order_update fires kitchen-routing/stock hooks
    return get_order(name)


@frappe.whitelist()
def cancel_order(name):
    require_restaurant_role()
    order = frappe.get_doc("Restaurant Order", name)
    if order.status in ("billed", "cancelled"):
        frappe.throw(f"A {order.status} order cannot be cancelled")
    order.status = "cancelled"
    order.save(ignore_permissions=True)
    return get_order(name)
