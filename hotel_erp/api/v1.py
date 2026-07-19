"""/api/v1 whitelisted methods — the external contract surface (§4.5).

Each method is dispatched either via the clean REST router (hotel_erp.api.router,
e.g. GET /api/v1/health) or directly at /api/method/hotel_erp.api.v1.<fn>.

Decorator stack for the four mutating endpoints (outer -> inner):
    @frappe.whitelist(allow_guest=True)   # framework entry; own bearer auth
    @api_endpoint()                       # auth + §4.9 error envelope
    @idempotent(scope=...)                # §4.10 idempotency, distinct scope each
    def ...
"""
from __future__ import annotations

import base64
import json

import frappe

from hotel_erp.api.common import (
    api_endpoint,
    iso_utc,
    parse_int,
    resolve_rate_plan,
    resolve_room_type,
    strip_slug,
    to_date,
)
from hotel_erp.api.errors import ApiError
from hotel_erp.api.serializers import serialize_hold, serialize_reservation, serialize_room_type
from hotel_erp.booking.atomic_hold import (
    RoomsUnavailableError,
    _nights,
    create_room_hold,
    release_room_hold,
)
from hotel_erp.sync.events import enqueue_availability_changed, namespaced
from hotel_erp.sync.idempotency import idempotent

MAX_LIMIT = 200
DEFAULT_LIMIT = 50


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
@api_endpoint(require_auth=False)
def get_health(**kwargs):
    config = frappe.get_single("Sync Config")
    return {
        "status": "ok",
        "api_version": "1.0",
        "hold_ttl_seconds": config.hold_ttl_seconds or 300,
        "server_time": iso_utc(frappe.utils.now_datetime()),
    }


# ---------------------------------------------------------------------------
# Room types
# ---------------------------------------------------------------------------
def _encode_cursor(name: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"after": name}).encode()).decode()


def _decode_cursor(cursor: str):
    if not cursor:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode()).get("after")
    except (ValueError, TypeError):
        raise ApiError("VALIDATION_ERROR", "Malformed cursor", 400)


@frappe.whitelist(allow_guest=True)
@api_endpoint()
def list_room_types(updated_since=None, cursor=None, limit=None, **kwargs):
    limit = min(max(parse_int(limit, DEFAULT_LIMIT), 1), MAX_LIMIT)
    after = _decode_cursor(cursor)

    filters = []
    if updated_since:
        filters.append(["modified", ">=", updated_since])
    if after:
        filters.append(["name", ">", after])

    rows = frappe.get_all(
        "Room Type",
        filters=filters,
        order_by="name asc",
        limit_page_length=limit + 1,
        pluck="name",
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    data = [serialize_room_type(frappe.get_doc("Room Type", name)) for name in rows]
    next_cursor = _encode_cursor(rows[-1]) if has_more and rows else None
    return {"data": data, "next_cursor": next_cursor}


@frappe.whitelist(allow_guest=True)
@api_endpoint()
def get_room_type(room_type_id=None, **kwargs):
    doc = resolve_room_type(room_type_id)
    return serialize_room_type(doc)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
def _calendar_rows(rate_plan_name: str, nights) -> dict:
    if not nights:
        return {}
    rows = frappe.db.sql(
        """
        SELECT date, price_minor, currency, rooms_available
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_name, "dates": tuple(nights)},
        as_dict=True,
    )
    return {r.date: r for r in rows}


@frappe.whitelist(allow_guest=True)
@api_endpoint()
def get_availability(
    room_type_id=None, check_in=None, check_out=None, rooms=None, adults=None, children=None, **kwargs
):
    room_type = resolve_room_type(room_type_id)
    ci = to_date(check_in)
    co = to_date(check_out)
    if co <= ci:
        raise ApiError("VALIDATION_ERROR", "check_out must be after check_in", 400)
    nights = _nights(ci, co)

    rate_plans = frappe.get_all(
        "Rate Plan",
        filters={"room_type": room_type.name, "active": 1},
        fields=["name", "code", "refundable"],
        order_by="code asc",
    )

    quotes = []
    for plan in rate_plans:
        by_date = _calendar_rows(plan.name, nights)
        if not by_date:
            continue
        currency = None
        total = 0
        nightly = []
        for night in nights:
            row = by_date.get(night)
            if row:
                currency = row.currency
                total += row.price_minor
                nightly.append(
                    {
                        "date": str(night),
                        "price_minor": row.price_minor,
                        "currency": row.currency,
                        "rooms_available": row.rooms_available,
                    }
                )
            else:
                nightly.append(
                    {
                        "date": str(night),
                        "price_minor": 0,
                        "currency": currency or "",
                        "rooms_available": 0,
                    }
                )
        if currency is None:
            continue
        quotes.append(
            {
                "rate_plan_code": plan.code,
                "refundable": bool(plan.refundable),
                "nightly_rates": nightly,
                "total_amount_minor": total,
                "currency": currency,
            }
        )

    return {
        "room_type_id": namespaced(room_type.code),
        "check_in": str(ci),
        "check_out": str(co),
        "rooms_requested": parse_int(rooms, 1),
        "quotes": quotes,
    }


# ---------------------------------------------------------------------------
# Reservation hold / confirm / release / cancel
# ---------------------------------------------------------------------------
def _as_dict(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


@frappe.whitelist(allow_guest=True)
@api_endpoint()
@idempotent(scope="reservations.hold")
def create_hold(
    room_type_id=None,
    rate_plan_code=None,
    check_in=None,
    check_out=None,
    rooms_requested=None,
    occupancy=None,
    requested_by="aggregator",
    **kwargs,
):
    room_type = resolve_room_type(room_type_id)
    rate_plan = resolve_rate_plan(room_type.name, rate_plan_code)

    ci = to_date(check_in)
    co = to_date(check_out)
    if co <= ci:
        raise ApiError("VALIDATION_ERROR", "check_out must be after check_in", 400)
    rooms = parse_int(rooms_requested, 1)
    if rooms < 1:
        raise ApiError("VALIDATION_ERROR", "rooms_requested must be >= 1", 400)

    nights = _nights(ci, co)
    by_date = _calendar_rows(rate_plan.name, nights)

    # Atomic multi-night check-and-decrement (NFR-A2). Surface unavailable nights
    # with the room_type_id in details, per §4.9's error example.
    try:
        create_room_hold(rate_plan.name, ci, co, rooms)
    except RoomsUnavailableError as e:
        raise ApiError(
            "ROOMS_UNAVAILABLE",
            "Requested room count is not available for one or more nights in the stay.",
            409,
            {"room_type_id": namespaced(room_type.code), "unavailable_dates": e.unavailable_dates},
        )

    total = sum(by_date[n].price_minor for n in nights if n in by_date)
    currency = next((by_date[n].currency for n in nights if n in by_date), "")

    config = frappe.get_single("Sync Config")
    ttl = config.hold_ttl_seconds or 300
    expires_at = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=ttl)

    channel = "direct" if requested_by == "direct" else "aggregator"
    hold = frappe.get_doc(
        {
            "doctype": "Reservation Hold",
            "room_type": room_type.name,
            "rate_plan": rate_plan.name,
            "check_in": ci,
            "check_out": co,
            "rooms_requested": rooms,
            "occupancy": frappe.as_json(_as_dict(occupancy) or {}),
            "channel": channel,
            "idempotency_key": frappe.get_request_header("Idempotency-Key"),
            "total_amount_minor": total,
            "currency": currency,
            "expires_at": expires_at,
            "status": "held",
        }
    ).insert(ignore_permissions=True)

    # One availability.changed per affected night (§4.7), transactional outbox.
    enqueue_availability_changed(room_type.name, rate_plan.name, ci, co)

    frappe.local.response["http_status_code"] = 201
    return serialize_hold(hold, room_type.code, rate_plan_code)


@frappe.whitelist(allow_guest=True)
@api_endpoint()
@idempotent(scope="reservations.confirm")
def confirm_hold(hold_id=None, payment_reference=None, guests=None, **kwargs):
    hold = _load_hold(hold_id)

    room_type_code = frappe.db.get_value("Room Type", hold.room_type, "code")
    rate_plan_code = frappe.db.get_value("Rate Plan", hold.rate_plan, "code")

    if hold.status == "confirmed":
        existing = frappe.db.get_value("Reservation", {"hold": hold.name}, "name")
        if existing:
            return serialize_reservation(
                frappe.get_doc("Reservation", existing), room_type_code, rate_plan_code
            )
    if hold.status in ("released", "expired"):
        raise ApiError("HOLD_EXPIRED", f"Hold is {hold.status} and can no longer be confirmed", 409)
    if hold.status == "held" and frappe.utils.now_datetime() > frappe.utils.get_datetime(hold.expires_at):
        raise ApiError("HOLD_EXPIRED", "Hold has expired", 409)

    guest_list = _as_dict(guests) or []
    if not guest_list:
        raise ApiError("VALIDATION_ERROR", "At least one guest is required", 400)

    reservation = frappe.get_doc(
        {
            "doctype": "Reservation",
            "hold": hold.name,
            "room_type": hold.room_type,
            "rate_plan": hold.rate_plan,
            "check_in": hold.check_in,
            "check_out": hold.check_out,
            "rooms_requested": hold.rooms_requested,
            "total_amount_minor": hold.total_amount_minor,
            "currency": hold.currency,
            "payment_reference": payment_reference,
            "status": "confirmed",
            "guests": [
                {
                    "guest_name": g.get("name"),
                    "phone": g.get("phone"),
                    "email": g.get("email"),
                }
                for g in guest_list
            ],
        }
    ).insert(ignore_permissions=True)

    frappe.db.set_value("Reservation Hold", hold.name, "status", "confirmed")

    # Inventory stays decremented at confirm (see atomic_hold docstring); emit
    # availability.changed to honour the §4.8 sequence diagram.
    enqueue_availability_changed(hold.room_type, hold.rate_plan, hold.check_in, hold.check_out)

    return serialize_reservation(reservation, room_type_code, rate_plan_code)


@frappe.whitelist(allow_guest=True)
@api_endpoint()
@idempotent(scope="reservations.release")
def release_hold(hold_id=None, **kwargs):
    hold = _load_hold(hold_id)
    room_type_code = frappe.db.get_value("Room Type", hold.room_type, "code")
    rate_plan_code = frappe.db.get_value("Rate Plan", hold.rate_plan, "code")

    if hold.status == "held":
        release_room_hold(hold.rate_plan, hold.check_in, hold.check_out, hold.rooms_requested)
        frappe.db.set_value("Reservation Hold", hold.name, "status", "released")
        hold.status = "released"
        enqueue_availability_changed(hold.room_type, hold.rate_plan, hold.check_in, hold.check_out)

    return serialize_hold(hold, room_type_code, rate_plan_code)


@frappe.whitelist(allow_guest=True)
@api_endpoint()
def get_reservation(reservation_id=None, **kwargs):
    reservation = _load_reservation(reservation_id)
    room_type_code = frappe.db.get_value("Room Type", reservation.room_type, "code")
    rate_plan_code = frappe.db.get_value("Rate Plan", reservation.rate_plan, "code")
    return serialize_reservation(reservation, room_type_code, rate_plan_code)


@frappe.whitelist(allow_guest=True)
@api_endpoint()
@idempotent(scope="reservations.cancel")
def cancel_reservation(reservation_id=None, **kwargs):
    reservation = _load_reservation(reservation_id)
    room_type_code = frappe.db.get_value("Room Type", reservation.room_type, "code")
    rate_plan = frappe.get_doc("Rate Plan", reservation.rate_plan)

    if reservation.status in ("checked_in", "checked_out", "no_show"):
        raise ApiError(
            "CANCELLATION_NOT_ALLOWED",
            f"A {reservation.status} reservation cannot be cancelled via this endpoint",
            422,
        )

    refund_percentage = _refund_percentage(rate_plan, reservation.check_in)

    if reservation.status != "cancelled":
        release_room_hold(
            reservation.rate_plan,
            reservation.check_in,
            reservation.check_out,
            reservation.rooms_requested,
        )
        frappe.db.set_value("Reservation", reservation.name, "status", "cancelled")
        reservation.status = "cancelled"
        enqueue_availability_changed(
            reservation.room_type, reservation.rate_plan, reservation.check_in, reservation.check_out
        )

    body = serialize_reservation(reservation, room_type_code, rate_plan.code)
    body["refund_percentage"] = refund_percentage
    return body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_hold(hold_id: str):
    name = strip_slug(hold_id)
    if not frappe.db.exists("Reservation Hold", name):
        raise ApiError("NOT_FOUND", f"Unknown hold '{hold_id}'", 404)
    return frappe.get_doc("Reservation Hold", name)


def _load_reservation(reservation_id: str):
    name = strip_slug(reservation_id)
    if not frappe.db.exists("Reservation", name):
        raise ApiError("NOT_FOUND", f"Unknown reservation '{reservation_id}'", 404)
    return frappe.get_doc("Reservation", name)


def _refund_percentage(rate_plan, check_in) -> float:
    """Derive the refund owed from the rate plan's cancellation policy (§4.8).
    Service B executes the actual refund; Service A only reports the percentage."""
    if not rate_plan.refundable:
        return 0.0
    hours = rate_plan.free_cancellation_until_hours_before_checkin
    if hours is None:
        return 100.0
    deadline = frappe.utils.add_to_date(frappe.utils.get_datetime(f"{check_in} 00:00:00"), hours=-hours)
    return 100.0 if frappe.utils.now_datetime() <= deadline else 0.0
