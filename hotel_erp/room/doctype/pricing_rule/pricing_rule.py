"""Pricing Rule (FR-A4).

A dynamic-pricing adjustment applied to a Rate Plan's `base_price_minor` by the
scheduled hotel_erp.pricing.rules.apply_pricing_rules job. Multiple rules on one
rate plan compose in `priority` order (lower first). See that module for the
per-`rule_type` matching semantics.
"""
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PricingRule(Document):
    def validate(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            frappe.throw("end_date must not be before start_date")
