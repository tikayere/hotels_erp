"""Response builders for the §4.4 canonical entity schemas.

Guest data is built EXCLUSIVELY from Reservation Guest child rows — never from
the internal Guest DocType, which carries identity documents that must never
cross the boundary (NFR-A9 / §5.6).
"""
from __future__ import annotations

import json

import frappe

from hotel_erp.api.common import iso_utc
from hotel_erp.sync.events import namespaced


def _json_list(value) -> list:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def serialize_room_type(doc) -> dict:
    return {
        "room_type_id": namespaced(doc.code),
        "name": doc.room_type_name,
        "description": doc.description or "",
        "max_occupancy_adults": doc.max_occupancy_adults,
        "max_occupancy_children": doc.max_occupancy_children or 0,
        "bed_config": doc.bed_config or "",
        "size_sqm": doc.size_sqm,
        "amenities": _json_list(doc.amenities),
        "photos": _json_list(doc.photos),
        "active": bool(doc.active),
        "updated_at": iso_utc(doc.modified),
    }


def serialize_hold(hold, room_type_code: str, rate_plan_code: str) -> dict:
    return {
        "hold_id": namespaced(hold.name),
        "room_type_id": namespaced(room_type_code),
        "rate_plan_code": rate_plan_code,
        "check_in": str(hold.check_in),
        "check_out": str(hold.check_out),
        "rooms_requested": hold.rooms_requested,
        "total_amount_minor": hold.total_amount_minor,
        "currency": hold.currency,
        "status": hold.status,
        "expires_at": iso_utc(hold.expires_at),
    }


def serialize_reservation(res, room_type_code: str, rate_plan_code: str) -> dict:
    # Guests come from Reservation Guest child rows ONLY (§5.6).
    guests = []
    for g in res.guests:
        guest = {"name": g.guest_name}
        if g.phone:
            guest["phone"] = g.phone
        if g.email:
            guest["email"] = g.email
        guests.append(guest)

    out = {
        "reservation_id": namespaced(res.name),
        "hold_id": namespaced(res.hold),
        "confirmation_number": res.confirmation_number,
        "room_type_id": namespaced(room_type_code),
        "rate_plan_code": rate_plan_code,
        "check_in": str(res.check_in),
        "check_out": str(res.check_out),
        "rooms_requested": res.rooms_requested,
        "status": res.status,
        "guests": guests,
        "total_amount_minor": res.total_amount_minor,
        "currency": res.currency,
        "created_at": iso_utc(res.creation),
    }
    if res.payment_reference:
        out["payment_reference"] = res.payment_reference
    return out
