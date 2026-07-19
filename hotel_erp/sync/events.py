"""Outbound event enqueueing (transactional outbox, NFR-A5 / contract §4.7).

Every function here inserts one or more Webhook Outbox rows *inside the caller's
existing DB transaction* — never sends HTTP itself. Delivery is the
dispatcher's job (hotel_erp.sync.dispatcher). This is what makes webhook
delivery crash-safe: the outbox row commits atomically with the domain write
that produced it.

ID namespacing (contract §4.1.7, doctype_spec.md §1.3): the "{hotel_slug}."
prefix is applied here, at the webhook boundary, reading hotel_slug once from
Sync Config. Domain documents store bare local IDs only.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import frappe

SCHEMA_VERSION = "1.0"


def get_hotel_slug() -> str:
    return frappe.db.get_single_value("Sync Config", "hotel_slug") or ""


def namespaced(local_id: str) -> str:
    slug = get_hotel_slug()
    return f"{slug}.{local_id}" if slug else local_id


def _nights(check_in: date, check_out: date) -> list[date]:
    n = (check_out - check_in).days
    return [check_in + timedelta(days=i) for i in range(n)]


def enqueue_event(event_type: str, data: dict) -> None:
    """Insert a single Webhook Outbox row wrapping `data` in the §4.4 envelope."""
    event_id = str(uuid.uuid4())
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "hotel_id": get_hotel_slug(),
        "schema_version": SCHEMA_VERSION,
        "occurred_at": frappe.utils.now_datetime().isoformat() + "Z",
        "data": data,
    }
    frappe.get_doc(
        {
            "doctype": "Webhook Outbox",
            "event_id": event_id,
            "event_type": event_type,
            "payload": frappe.as_json(envelope),
            "status": "pending",
        }
    ).insert(ignore_permissions=True)


def enqueue_availability_changed(room_type_name: str, rate_plan_name: str, check_in: date, check_out: date) -> None:
    """One availability.changed event per affected night (contract §4.7) — the
    per-(room_type, date, rate_plan) shape Rate Calendar uses. Reads the current
    Rate Calendar rows so each event carries the post-change rooms_available."""
    rate_plan_code, refundable = frappe.db.get_value("Rate Plan", rate_plan_name, ["code", "refundable"])
    room_type_code = frappe.db.get_value("Room Type", room_type_name, "code")
    nights = _nights(check_in, check_out)
    if not nights:
        return
    rows = frappe.db.sql(
        """
        SELECT date, rooms_available, price_minor, currency
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_name, "dates": tuple(nights)},
        as_dict=True,
    )
    for row in rows:
        enqueue_event(
            "availability.changed",
            {
                "room_type_id": namespaced(room_type_code),
                "date": str(row.date),
                "rate_plan_code": rate_plan_code,
                "rooms_available": row.rooms_available,
                "price_minor": row.price_minor,
                "currency": row.currency,
                "refundable": bool(refundable),
            },
        )


def enqueue_reservation_status_event(event_type: str, room_type_name: str, reservation_name: str) -> None:
    """reservation.checked_in / checked_out / no_show — IDs only, never guest
    identity data (contract §4.7 note / §5.6)."""
    room_type_code = frappe.db.get_value("Room Type", room_type_name, "code")
    enqueue_event(
        event_type,
        {
            "reservation_id": namespaced(reservation_name),
            "room_type_id": namespaced(room_type_code),
        },
    )


def enqueue_room_type_event(event_type: str, room_type_name: str) -> None:
    """room_type.created / room_type.updated / room_type.deleted (contract §4.7)."""
    from hotel_erp.api.serializers import serialize_room_type

    if event_type == "room_type.deleted":
        room_type_code = frappe.db.get_value("Room Type", room_type_name, "code")
        enqueue_event(event_type, {"room_type_id": namespaced(room_type_code)})
    else:
        doc = frappe.get_doc("Room Type", room_type_name)
        enqueue_event(event_type, serialize_room_type(doc))
