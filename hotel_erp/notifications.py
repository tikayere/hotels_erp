"""Guest-facing email notifications (Wave B of ENTERPRISE_READINESS_PLAN.md).

Booking confirmation, cancellation, and checkout-receipt emails, all sent
via Frappe's own `frappe.sendmail` (queued through whatever Email Account
the deploying operator configures in Desk — Settings > Email Account. No
SMTP credentials are baked into this app; until one is configured,
`frappe.sendmail` itself will fail, which is why every call here is
wrapped so a mail failure never blocks the booking/checkout/cancel flow
that triggered it — it's logged via `frappe.log_error` instead, not raised.

Silently no-ops if the reservation has no guest email on file (a valid
state — not every guest gives one, especially phone-in/walk-in bookings).
"""
from __future__ import annotations

import frappe


def _first_guest_email(doc) -> str | None:
    for g in doc.guests or []:
        if g.email:
            return g.email
    return None


def _guest_name(doc) -> str:
    for g in doc.guests or []:
        if g.guest_name:
            return g.guest_name
    return "Guest"


def _property_name(doc) -> str:
    property_name = frappe.db.get_value("Room Type", doc.room_type, "property")
    if property_name:
        return frappe.db.get_value("Property", property_name, "property_name") or "your hotel"
    return "your hotel"


def send_booking_confirmation(doc) -> None:
    email = _first_guest_email(doc)
    if not email:
        return
    try:
        frappe.sendmail(
            recipients=[email],
            subject=f"Booking confirmed — {doc.confirmation_number}",
            message=frappe.render_template(
                """
                <p>Dear {{ guest_name }},</p>
                <p>Your reservation at {{ property_name }} is confirmed.</p>
                <ul>
                  <li><b>Confirmation number:</b> {{ confirmation_number }}</li>
                  <li><b>Check-in:</b> {{ check_in }}</li>
                  <li><b>Check-out:</b> {{ check_out }}</li>
                  <li><b>Total:</b> {{ total }}</li>
                </ul>
                <p>We look forward to welcoming you.</p>
                """,
                {
                    "guest_name": _guest_name(doc),
                    "property_name": _property_name(doc),
                    "confirmation_number": doc.confirmation_number,
                    "check_in": doc.get_formatted("check_in"),
                    "check_out": doc.get_formatted("check_out"),
                    "total": f"{(doc.total_amount_minor or 0) / 100:.2f} {doc.currency}",
                },
            ),
            now=True,
        )
    except Exception:
        frappe.log_error(title="Booking confirmation email failed", message=frappe.get_traceback())


def send_cancellation_email(doc) -> None:
    email = _first_guest_email(doc)
    if not email:
        return
    try:
        frappe.sendmail(
            recipients=[email],
            subject=f"Booking cancelled — {doc.confirmation_number}",
            message=frappe.render_template(
                """
                <p>Dear {{ guest_name }},</p>
                <p>Your reservation {{ confirmation_number }} ({{ check_in }} – {{ check_out }})
                at {{ property_name }} has been cancelled.</p>
                <p>If you did not request this, please contact the property directly.</p>
                """,
                {
                    "guest_name": _guest_name(doc),
                    "property_name": _property_name(doc),
                    "confirmation_number": doc.confirmation_number,
                    "check_in": doc.get_formatted("check_in"),
                    "check_out": doc.get_formatted("check_out"),
                },
            ),
            now=True,
        )
    except Exception:
        frappe.log_error(title="Cancellation email failed", message=frappe.get_traceback())


def send_checkout_receipt(doc) -> None:
    email = _first_guest_email(doc)
    if not email:
        return
    try:
        pdf = frappe.get_print(doc.doctype, doc.name, print_format="Reservation Folio", as_pdf=True)
        frappe.sendmail(
            recipients=[email],
            subject=f"Your receipt — {doc.confirmation_number}",
            message=frappe.render_template(
                """
                <p>Dear {{ guest_name }},</p>
                <p>Thank you for staying with {{ property_name }}. Your receipt for
                {{ confirmation_number }} is attached.</p>
                """,
                {
                    "guest_name": _guest_name(doc),
                    "property_name": _property_name(doc),
                    "confirmation_number": doc.confirmation_number,
                },
            ),
            attachments=[{"fname": f"{doc.confirmation_number}-receipt.pdf", "fcontent": pdf}],
            now=True,
        )
    except Exception:
        frappe.log_error(title="Checkout receipt email failed", message=frappe.get_traceback())
