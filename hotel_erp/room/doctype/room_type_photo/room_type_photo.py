"""Room Type Photo — child table of Room Type.

Gives Room Type a real drag-and-drop image upload widget per row (Attach
Image) instead of hand-typed URLs. Row order (idx) controls display order,
so row 0 is the cover photo used by the Portal/Web listing cards.
"""
from __future__ import annotations

from frappe.model.document import Document


class RoomTypePhoto(Document):
    pass
