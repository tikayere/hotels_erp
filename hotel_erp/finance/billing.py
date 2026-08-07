"""Folio/billing helpers.

Before this module existed, `Finance Txn` was a 100%-manual ledger --
nothing ever auto-posted a charge, not even room revenue at booking time,
and the pre-existing `Reservation Folio` print format's "Charges" table
(which reads `Finance Txn` rows) was always empty in practice. This module
closes that gap: it auto-posts the room charge at booking and the
restaurant charge when an order is marked `billed`, and gives front desk a
real, computed balance-due figure plus a way to record an offline payment
against it (`get_folio` / `record_payment`).

Deliberately manual/offline payments only -- `payment_method` is a plain
Select (cash/mobile_money/bank_transfer/card/other), there's no gateway
integration here. See ENTERPRISE_READINESS_PLAN.md Wave A: payment-gateway
wiring (`frappe/payments`) is an explicit future phase, not this one.
"""
from __future__ import annotations

import frappe

# "Charges" increase what's owed, "credits" reduce it -- balance_due is
# charges minus credits. `tax` is included as a charge type even though
# nothing currently auto-posts one (no tax-calculation workflow exists
# yet) so a manually-entered tax line still balances correctly.
_CHARGE_TYPES = ("revenue", "tax")
_CREDIT_TYPES = ("refund", "payment")


def post_room_charge(reservation) -> None:
    """Reservation.after_insert: post the whole-stay room-charge revenue
    line. The amount is already fixed at booking time
    (`total_amount_minor`, computed by the booking/hold-confirm flow
    itself) -- this doesn't recompute anything, just makes it a visible
    ledger entry instead of a number that only ever lived on the
    Reservation doc."""
    if not reservation.total_amount_minor:
        return
    _post_txn(
        txn_type="revenue",
        amount_minor=reservation.total_amount_minor,
        currency=reservation.currency,
        reservation=reservation.name,
        ref=reservation.name,
    )


def post_restaurant_charge(order) -> None:
    """Restaurant Order transitioning to `billed`: post its revenue line,
    linked to the guest's folio if this was a room order (`order.reservation`
    set) -- a walk-in dine-in sale with no reservation still posts (real
    restaurant revenue either way), just isn't attached to any folio."""
    if not order.amount_minor:
        return
    _post_txn(
        txn_type="revenue",
        amount_minor=order.amount_minor,
        currency=order.currency,
        reservation=order.reservation or None,
        ref=order.reservation or order.name,
    )


def post_maintenance_expense(request) -> None:
    """Maintenance Request resolved/closed with a `cost_minor` set: post the
    repair cost as an expense line, so it shows up in the same ledger as
    everything else instead of living only on the request document.
    `currency` is required on Finance Txn, so this silently no-ops (rather
    than 500ing the status-change save) if cost was entered without one."""
    if not request.cost_minor or not request.currency:
        return
    _post_txn(
        txn_type="expense",
        amount_minor=request.cost_minor,
        currency=request.currency,
        ref=request.name,
    )


def post_conference_revenue(booking) -> None:
    """Conference Booking confirmed with a `total_amount_minor` set: post
    the booking's revenue line. Same currency-required no-op rule as
    `post_maintenance_expense`."""
    if not booking.total_amount_minor or not booking.currency:
        return
    _post_txn(
        txn_type="revenue",
        amount_minor=booking.total_amount_minor,
        currency=booking.currency,
        ref=booking.name,
    )


def _post_txn(*, txn_type, amount_minor, currency, reservation=None, ref=None, payment_method=None) -> str:
    doc = frappe.get_doc(
        {
            "doctype": "Finance Txn",
            "type": txn_type,
            "amount_minor": amount_minor,
            "currency": currency,
            "reservation": reservation,
            "ref": ref,
            "payment_method": payment_method,
        }
    ).insert(ignore_permissions=True)
    doc.submit()
    return doc.name


def get_folio(reservation_name: str) -> dict:
    """Itemized charges/payments + computed balance for one reservation --
    only `docstatus=1` rows count (a draft/cancelled txn isn't a real
    ledger entry, matching `get_summary`'s own convention in api/finance.py)."""
    rows = frappe.get_all(
        "Finance Txn",
        filters={"reservation": reservation_name, "docstatus": 1},
        fields=["name", "type", "amount_minor", "currency", "payment_method", "creation"],
        order_by="creation asc",
    )
    charges = sum(r.amount_minor for r in rows if r.type in _CHARGE_TYPES)
    credits = sum(r.amount_minor for r in rows if r.type in _CREDIT_TYPES)
    currency = next((r.currency for r in rows), None)
    return {
        "lines": rows,
        "charges_minor": charges,
        "credits_minor": credits,
        "balance_due_minor": charges - credits,
        "currency": currency,
    }


def record_payment(reservation_name: str, amount_minor: int, currency: str, method: str) -> str:
    amount_minor = int(amount_minor)
    if amount_minor <= 0:
        frappe.throw("Payment amount must be greater than zero")
    if not frappe.db.exists("Reservation", reservation_name):
        frappe.throw("Unknown reservation")
    valid_methods = ("cash", "mobile_money", "bank_transfer", "card", "other")
    if method not in valid_methods:
        frappe.throw(f"method must be one of: {', '.join(valid_methods)}")
    return _post_txn(
        txn_type="payment",
        amount_minor=amount_minor,
        currency=currency,
        reservation=reservation_name,
        ref=reservation_name,
        payment_method=method,
    )
