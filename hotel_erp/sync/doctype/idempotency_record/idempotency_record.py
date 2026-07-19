"""Idempotency Record — backs the @idempotent decorator (contract §4.10).

`name` is the caller-supplied scope+key hash (see hotel_erp.sync.idempotency),
so the DocType is named "Set by user"/prompt rather than auto-generated.
"""
from __future__ import annotations

from frappe.model.document import Document


class IdempotencyRecord(Document):
    pass
