"""Dynamic pricing (FR-A4).

`apply_pricing_rules` runs daily: for every active Rate Plan that has a
`base_price_minor` set, it recomputes each existing Rate Calendar row in the
rolling horizon (today onward) from the base price by composing that plan's
active Pricing Rules in `priority` order (lower first). When a night's computed
price differs from its stored `price_minor`, the row is updated and a
`rate.changed` webhook is emitted for that night (contract §4.7, "same shape as
availability.changed").

This only *reprices* existing rows — it never creates new Rate Calendar rows;
horizon pre-population is a separate concern (doctype_spec.md §3 Rate Calendar
note).

Per-`rule_type` matching (a rule matches a specific calendar date when):
  * season / holiday : start_date <= date <= end_date (both must be set)
  * day_of_week      : date.weekday() (Monday=0 .. Sunday=6) is in days_of_week
  * lead_time        : (date - today).days is within
                       [lead_time_days_min, lead_time_days_max] (open-ended if
                       a bound is unset)
  * occupancy        : that night's rooms_available <= occupancy_threshold_percent.
                       Interpreted deliberately as an ABSOLUTE remaining-room-count
                       threshold, not a true occupancy percentage — the Rate
                       Calendar tracks rooms_available, not a total-inventory
                       baseline, so a genuine occupancy-rate calc would need a
                       per-room-type room count join that adds complexity without
                       changing the rule's intent ("raise price as rooms run low").

Adjustments (composed in priority order):
  * percentage    : new_price = round(new_price * (1 + adjustment_value / 100))
  * fixed_amount  : new_price += adjustment_value
A computed price is never allowed below 0.
"""
from __future__ import annotations

from datetime import date

import frappe

from hotel_erp.sync.events import enqueue_rate_changed


def _rule_matches(rule, the_date: date, rooms_available: int, today: date) -> bool:
    rt = rule.rule_type
    if rt in ("season", "holiday"):
        if not rule.start_date or not rule.end_date:
            return False
        return frappe.utils.getdate(rule.start_date) <= the_date <= frappe.utils.getdate(rule.end_date)
    if rt == "day_of_week":
        days = rule.days_of_week
        if isinstance(days, str):
            days = frappe.parse_json(days)
        if not days:
            return False
        return the_date.weekday() in [int(d) for d in days]
    if rt == "lead_time":
        lead = (the_date - today).days
        if rule.lead_time_days_min is not None and lead < rule.lead_time_days_min:
            return False
        if rule.lead_time_days_max is not None and lead > rule.lead_time_days_max:
            return False
        return True
    if rt == "occupancy":
        if rule.occupancy_threshold_percent is None:
            return False
        return rooms_available <= rule.occupancy_threshold_percent
    return False


def _apply_adjustment(price: int, rule) -> int:
    if rule.adjustment_type == "percentage":
        price = round(price * (1 + rule.adjustment_value / 100))
    else:  # fixed_amount
        price = price + rule.adjustment_value
    return max(int(price), 0)


def apply_pricing_rules() -> None:
    today = frappe.utils.getdate(frappe.utils.today())

    rate_plans = frappe.get_all(
        "Rate Plan",
        filters={"active": 1, "base_price_minor": ["is", "set"]},
        fields=["name", "room_type", "base_price_minor"],
    )

    for plan in rate_plans:
        base = plan.base_price_minor
        if base is None:
            continue

        rules = frappe.get_all(
            "Pricing Rule",
            filters={"rate_plan": plan.name, "active": 1},
            fields=[
                "rule_type", "start_date", "end_date", "days_of_week",
                "lead_time_days_min", "lead_time_days_max", "occupancy_threshold_percent",
                "adjustment_type", "adjustment_value", "priority",
            ],
            order_by="priority asc",
        )

        rows = frappe.get_all(
            "Rate Calendar",
            filters={"rate_plan": plan.name, "date": [">=", today]},
            fields=["name", "date", "price_minor", "rooms_available"],
        )

        changed_dates = []
        for row in rows:
            the_date = frappe.utils.getdate(row.date)
            new_price = base
            for rule in rules:
                if _rule_matches(rule, the_date, row.rooms_available, today):
                    new_price = _apply_adjustment(new_price, rule)
            new_price = max(int(new_price), 0)
            if new_price != row.price_minor:
                frappe.db.set_value("Rate Calendar", row.name, "price_minor", new_price)
                changed_dates.append(the_date)

        if changed_dates:
            enqueue_rate_changed(plan.room_type, plan.name, changed_dates)
            # Commit per rate plan so a crash mid-run keeps already-repriced
            # plans and their emitted rate.changed events durable.
            frappe.db.commit()
