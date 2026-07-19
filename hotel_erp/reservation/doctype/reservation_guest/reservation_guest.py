"""Reservation Guest — child table of Reservation.

Deliberately minimal (name/phone/email only). Guest identity documents
(passport, national ID) live ONLY on the internal Guest DocType and must never
be copied here — this is the only guest data the §4.5 API is ever allowed to
serialize (NFR-A9 / §5.6).
"""
from __future__ import annotations

from frappe.model.document import Document


class ReservationGuest(Document):
    pass
