"""Guest — FR-A6, internal only.

NFR-A9 / §5.6: passport_no and national_id, and this DocType as a whole, MUST
NEVER cross the API boundary. The "Hotel API" role is deliberately granted NO
permission here (see the permissions block in guest.json) as a defense-in-depth
backstop: the §4.5 response serializers build guest data exclusively from
Reservation Guest rows, never from this DocType.
"""
from __future__ import annotations

from frappe.model.document import Document


class Guest(Document):
    pass
