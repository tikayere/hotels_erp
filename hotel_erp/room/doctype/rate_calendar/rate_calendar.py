"""Rate Calendar controller.

The single source of truth for both nightly pricing and inventory. The
`rooms_available >= 0` invariant is enforced inside the atomic hold transaction
(hotel_erp.booking.atomic_hold), never by form-level validation — see that
module's docstring and doctype_spec.md §3.
"""
from __future__ import annotations

from frappe.model.document import Document


class RateCalendar(Document):
    pass
