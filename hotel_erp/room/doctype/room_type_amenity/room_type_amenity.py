"""Room Type Amenity — child table of Room Type.

Replaces hand-typed JSON array syntax with one row per amenity, same
usability fix as Room Type Photo for the `photos` field.
"""
from __future__ import annotations

from frappe.model.document import Document


class RoomTypeAmenity(Document):
    pass
