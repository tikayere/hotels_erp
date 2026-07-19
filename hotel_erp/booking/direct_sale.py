"""Direct / walk-in sales (FR-A18).

A front-desk booking created *inside* Service A by a logged-in Frappe desk user
(role `Hotel Front Desk` or `Revenue Manager`), not by the Aggregator over the
bearer-token API. It decrements exactly the same Rate Calendar inventory an
Aggregator hold would (via hotel_erp.booking.atomic_hold), and emits the same
`availability.changed` events, so Service B's cache never drifts (FR-A18).

Unlike the /api/v1 contract surface this method:
  * authenticates with Frappe's own session/role layer, not `Authorization:
    Bearer` (contract §4.2) — so it takes plain LOCAL codes (`DLX-KING`,
    `FLEX`), never the namespaced `{hotel_slug}.` form the Aggregator sends;
  * needs no Idempotency-Key (§4.10) — a live desk user is not a retry-prone
    network client;
  * surfaces failures as plain `frappe.throw()` for the Desk UI, not the §4.9
    JSON error envelope.

It creates a `Reservation Hold` (channel="direct") and immediately a confirmed
`Reservation` in one call — the Reservation DocType's `hold` field is `reqd`,
so the Hold is created rather than skipped. The guest-privacy boundary
(NFR-A9 / §5.6) is identical here: guests are stored as `Reservation Guest`
child rows only, never on the internal `Guest` DocType.
"""
from __future__ import annotations

import json

import frappe

from hotel_erp.api.common import _call_with_deadlock_retry
from hotel_erp.api.serializers import serialize_reservation
from hotel_erp.booking.atomic_hold import RoomsUnavailableError, _nights, create_room_hold
from hotel_erp.sync.events import enqueue_availability_changed

_DESK_ROLES = ("Hotel Front Desk", "Revenue Manager", "System Manager")


def _as_dict(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


@frappe.whitelist()
def create_walkin_reservation(
    room_type_id=None,
    rate_plan_code=None,
    check_in=None,
    check_out=None,
    rooms_requested=None,
    occupancy=None,
    guests=None,
    **kwargs,
):
    """Create a confirmed walk-in reservation as the current desk user.

    `room_type_id` / `rate_plan_code` are BARE local codes (e.g. `DLX-KING`,
    `FLEX`) — this is an internal desk call, not an Aggregator call, so no
    namespacing is applied or expected. Returns the same shape
    serialize_reservation produces for the /api/v1 reservation endpoints.
    """
    # --- Auth: session role, not bearer (contract §4.2 does not apply here) ---
    if frappe.session.user in ("", "Guest"):
        frappe.throw("Authentication required", frappe.PermissionError)
    if not set(frappe.get_roles(frappe.session.user)) & set(_DESK_ROLES):
        frappe.throw(
            "Only Hotel Front Desk or Revenue Manager users may create walk-in reservations",
            frappe.PermissionError,
        )

    # --- Resolve local codes directly (no strip_slug / namespacing) ---
    room_type_name = frappe.db.get_value("Room Type", {"code": room_type_id}, "name")
    if not room_type_name:
        frappe.throw(f"Unknown room type '{room_type_id}'")
    rate_plan_name = frappe.db.get_value(
        "Rate Plan", {"room_type": room_type_name, "code": rate_plan_code}, "name"
    )
    if not rate_plan_name:
        frappe.throw(f"Unknown rate plan '{rate_plan_code}' for room type '{room_type_id}'")

    ci = frappe.utils.getdate(check_in)
    co = frappe.utils.getdate(check_out)
    if not ci or not co or co <= ci:
        frappe.throw("check_out must be after check_in")
    rooms = int(rooms_requested or 1)
    if rooms < 1:
        frappe.throw("rooms_requested must be >= 1")

    guest_list = _as_dict(guests) or []
    if not guest_list:
        frappe.throw("At least one guest is required")

    nights = _nights(ci, co)

    # Atomic multi-night check-and-decrement (NFR-A2), same code path as the
    # Aggregator hold. Wrapped in the shared deadlock-retry helper so a lost
    # Rate Calendar row-lock race under concurrent front-desk + Aggregator load
    # retries rather than 500s (see api/common._call_with_deadlock_retry).
    try:
        _call_with_deadlock_retry(create_room_hold, (rate_plan_name, ci, co, rooms), {})
    except RoomsUnavailableError as e:
        frappe.throw(
            "Requested room count is not available for one or more nights: "
            + ", ".join(e.unavailable_dates)
        )

    # Price/currency from the just-locked Rate Calendar rows.
    rows = frappe.db.sql(
        """
        SELECT date, price_minor, currency
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_name, "dates": tuple(nights)},
        as_dict=True,
    )
    by_date = {r.date: r for r in rows}
    total = sum(by_date[n].price_minor for n in nights if n in by_date)
    currency = next((by_date[n].currency for n in nights if n in by_date), "")

    config = frappe.get_single("Sync Config")
    ttl = config.hold_ttl_seconds or 300
    expires_at = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=ttl)

    hold = frappe.get_doc(
        {
            "doctype": "Reservation Hold",
            "room_type": room_type_name,
            "rate_plan": rate_plan_name,
            "check_in": ci,
            "check_out": co,
            "rooms_requested": rooms,
            "occupancy": frappe.as_json(_as_dict(occupancy) or {}),
            "channel": "direct",
            # No Idempotency-Key header on a desk call; synthesise a unique key
            # to satisfy the (room_type, idempotency_key) unique index / reqd field.
            "idempotency_key": f"walkin-{frappe.generate_hash(length=10)}",
            "total_amount_minor": total,
            "currency": currency,
            "expires_at": expires_at,
            "status": "held",
        }
    ).insert(ignore_permissions=True)

    reservation = frappe.get_doc(
        {
            "doctype": "Reservation",
            "hold": hold.name,
            "room_type": room_type_name,
            "rate_plan": rate_plan_name,
            "check_in": ci,
            "check_out": co,
            "rooms_requested": rooms,
            "total_amount_minor": total,
            "currency": currency,
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

    # One availability.changed per affected night (§4.7) — the Aggregator's
    # cache must reflect direct-sale inventory too (FR-A18).
    enqueue_availability_changed(room_type_name, rate_plan_name, ci, co)

    return serialize_reservation(reservation, room_type_id, rate_plan_code)
