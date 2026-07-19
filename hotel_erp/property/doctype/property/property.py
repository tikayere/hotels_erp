from __future__ import annotations

from frappe.model.document import Document


class Property(Document):
    def validate(self):
        if self.star_rating is not None and self.star_rating not in range(1, 6):
            from frappe import throw

            throw("star_rating must be between 1 and 5")
