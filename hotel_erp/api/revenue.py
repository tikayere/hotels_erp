"""Session-authenticated internal API for the Revenue Management module of
the `/pms` SPA -- Rate Plans, Pricing Rules, and the Rate Calendar. This is
the one module previously Desk-only (see memory `front_desk_spa`): a real
small/mid hotel's revenue manager needs to set prices and see the calendar
without dropping into Desk, so this closes that gap (ENTERPRISE_READINESS_PLAN.md
Wave D).

Restricted throughout to `pms_common.REVENUE_ROLES` (Revenue Manager + System
Manager), matching Rate Plan/Pricing Rule/Rate Calendar's own DocType
`permissions` blocks exactly -- pricing strategy isn't front-desk-readable
the way a room status is.
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate

from hotel_erp.api.pms_common import require_revenue_role
from hotel_erp.pricing.rules import apply_pricing_rules

_RULE_TYPES = ("season", "holiday", "day_of_week", "lead_time", "occupancy")
_ADJUSTMENT_TYPES = ("percentage", "fixed_amount")


def _as_json_or_none(value):
    """Pricing Rule.days_of_week is a `JSON` fieldtype -- Frappe's own
    base_document.get_valid_dict() throws "Value for X cannot be a list" for
    ANY non-table fieldtype given a raw Python list (see frappe/model/
    base_document.py's `_validate_length`), and frappe-ui's `call()` posts a
    JSON body (`Content-Type: application/json`), so a JS array param
    arrives here as a genuine Python list, not a pre-serialized string --
    unlike a form-encoded request where it would already be a string. Always
    normalize to a JSON string before it reaches `frappe.get_doc()`/`doc.set()`,
    same fix `pricing/rules.py`'s `_rule_matches()` expects on the read side
    (`frappe.parse_json(days)` when it's a str)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return frappe.as_json(value)


# ---------------------------------------------------------------------------
# Rate Plans
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_rate_plans(room_type=None, property=None):
    require_revenue_role()
    filters: dict = {}
    if room_type:
        filters["room_type"] = room_type
    if property:
        room_types = frappe.get_all("Room Type", filters={"property": property}, pluck="name")
        filters["room_type"] = ["in", room_types or [""]]
    plans = frappe.get_all(
        "Rate Plan",
        filters=filters,
        fields=[
            "name", "room_type", "code", "plan_name", "refundable",
            "free_cancellation_until_hours_before_checkin", "includes_breakfast",
            "base_price_minor", "active",
        ],
        order_by="plan_name",
    )
    if not plans:
        return []
    type_names = {p.room_type for p in plans}
    type_labels = dict(
        frappe.get_all("Room Type", filters={"name": ["in", list(type_names)]}, fields=["name", "room_type_name"], as_list=True)
    )
    # frappe.get_all() rejects a raw "count(name) as count" field string on
    # this Frappe version (same constraint noted in api/pms.py's
    # get_dashboard) -- plain SQL for the GROUP BY aggregate, matching that
    # existing convention.
    rule_counts = {
        row["rate_plan"]: row["count"]
        for row in frappe.db.sql(
            "SELECT rate_plan, COUNT(name) AS count FROM `tabPricing Rule` "
            "WHERE rate_plan IN %(plans)s AND active = 1 GROUP BY rate_plan",
            {"plans": tuple(p.name for p in plans)},
            as_dict=True,
        )
    }
    for p in plans:
        p["room_type_name"] = type_labels.get(p.room_type, p.room_type)
        p["active_rule_count"] = rule_counts.get(p.name, 0)
    return plans


@frappe.whitelist()
def get_rate_plan(name):
    require_revenue_role()
    plan = frappe.get_doc("Rate Plan", name).as_dict()
    plan["pricing_rules"] = frappe.get_all(
        "Pricing Rule",
        filters={"rate_plan": name},
        fields=[
            "name", "rule_name", "rule_type", "start_date", "end_date", "days_of_week",
            "lead_time_days_min", "lead_time_days_max", "occupancy_threshold_percent",
            "adjustment_type", "adjustment_value", "priority", "active",
        ],
        order_by="priority asc",
    )
    today = getdate()
    plan["upcoming_calendar"] = frappe.get_all(
        "Rate Calendar",
        filters={"rate_plan": name, "date": [">=", today]},
        fields=["name", "date", "price_minor", "currency", "rooms_available"],
        order_by="date asc",
        limit_page_length=14,
    )
    return plan


@frappe.whitelist()
def create_rate_plan(room_type, code, plan_name, base_price_minor=None, refundable=1,
                      includes_breakfast=0, free_cancellation_until_hours_before_checkin=None):
    require_revenue_role()
    doc = frappe.get_doc({
        "doctype": "Rate Plan",
        "room_type": room_type,
        "code": code,
        "plan_name": plan_name,
        "base_price_minor": base_price_minor,
        "refundable": refundable,
        "includes_breakfast": includes_breakfast,
        "free_cancellation_until_hours_before_checkin": free_cancellation_until_hours_before_checkin,
    }).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def update_rate_plan(name, **kwargs):
    require_revenue_role()
    doc = frappe.get_doc("Rate Plan", name)
    for field in (
        "plan_name", "base_price_minor", "refundable", "includes_breakfast",
        "free_cancellation_until_hours_before_checkin", "active",
    ):
        if field in kwargs and kwargs[field] is not None:
            doc.set(field, kwargs[field])
    doc.save(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Pricing Rules
# ---------------------------------------------------------------------------
@frappe.whitelist()
def create_pricing_rule(rate_plan, rule_name, rule_type, adjustment_type, adjustment_value,
                         start_date=None, end_date=None, days_of_week=None,
                         lead_time_days_min=None, lead_time_days_max=None,
                         occupancy_threshold_percent=None, priority=0):
    require_revenue_role()
    if rule_type not in _RULE_TYPES:
        frappe.throw(f"rule_type must be one of: {', '.join(_RULE_TYPES)}")
    if adjustment_type not in _ADJUSTMENT_TYPES:
        frappe.throw(f"adjustment_type must be one of: {', '.join(_ADJUSTMENT_TYPES)}")
    doc = frappe.get_doc({
        "doctype": "Pricing Rule",
        "rate_plan": rate_plan,
        "rule_name": rule_name,
        "rule_type": rule_type,
        "start_date": start_date,
        "end_date": end_date,
        "days_of_week": _as_json_or_none(days_of_week),
        "lead_time_days_min": lead_time_days_min,
        "lead_time_days_max": lead_time_days_max,
        "occupancy_threshold_percent": occupancy_threshold_percent,
        "adjustment_type": adjustment_type,
        "adjustment_value": adjustment_value,
        "priority": priority,
        "active": 1,
    }).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def update_pricing_rule(name, **kwargs):
    require_revenue_role()
    doc = frappe.get_doc("Pricing Rule", name)
    for field in (
        "rule_name", "rule_type", "start_date", "end_date", "days_of_week",
        "lead_time_days_min", "lead_time_days_max", "occupancy_threshold_percent",
        "adjustment_type", "adjustment_value", "priority", "active",
    ):
        if field in kwargs and kwargs[field] is not None:
            value = _as_json_or_none(kwargs[field]) if field == "days_of_week" else kwargs[field]
            doc.set(field, value)
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def delete_pricing_rule(name):
    require_revenue_role()
    frappe.delete_doc("Pricing Rule", name, ignore_permissions=True)
    return {"deleted": name}


# ---------------------------------------------------------------------------
# Rate Calendar
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_rate_calendar(rate_plan, start_date=None, end_date=None):
    require_revenue_role()
    start = getdate(start_date) if start_date else getdate()
    end = getdate(end_date) if end_date else add_days(start, 30)
    rows = frappe.get_all(
        "Rate Calendar",
        filters={"rate_plan": rate_plan, "date": ["between", [start, end]]},
        fields=["name", "date", "price_minor", "currency", "rooms_available"],
        order_by="date asc",
    )
    return {"rate_plan": rate_plan, "start_date": str(start), "end_date": str(end), "rows": rows}


@frappe.whitelist()
def upsert_rate_calendar_row(rate_plan, date, price_minor, currency, rooms_available):
    """Manual single-night override -- the nightly `apply_pricing_rules` job
    will reprice this row again from the Rate Plan's base price + active
    Pricing Rules the next time it runs, so this is a same-day / short-term
    correction tool, not a permanent pin."""
    require_revenue_role()
    existing = frappe.db.get_value("Rate Calendar", {"rate_plan": rate_plan, "date": date}, "name")
    if existing:
        doc = frappe.get_doc("Rate Calendar", existing)
        doc.price_minor = price_minor
        doc.currency = currency
        doc.rooms_available = rooms_available
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Rate Calendar",
            "rate_plan": rate_plan,
            "date": date,
            "price_minor": price_minor,
            "currency": currency,
            "rooms_available": rooms_available,
        }).insert(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist()
def recalculate_now():
    """Manually trigger the same reprice pass the nightly scheduler runs
    (`hotel_erp.pricing.rules.apply_pricing_rules`) -- lets a revenue manager
    see the effect of a rule change immediately instead of waiting for the
    next scheduled run."""
    require_revenue_role()
    apply_pricing_rules()
    return {"ok": True}
