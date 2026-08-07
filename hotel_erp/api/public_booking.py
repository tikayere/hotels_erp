"""Guest-facing, unauthenticated booking API for the public "Book Direct"
portal (`/book`, see `hotel_erp.www.book` + `frontend-guest/`).

Every method here is `@frappe.whitelist(allow_guest=True)` -- there is no
session, no bearer token, and no desk role check, unlike:

  * `hotel_erp.api.v1` -- the Aggregator's bearer-token contract (§4.2),
  * `hotel_erp.booking.direct_sale` -- desk-user walk-in sales (session +
    `Hotel Front Desk`/`Revenue Manager` role).

It shares the same underlying inventory primitive (`hotel_erp.booking.
atomic_hold.create_room_hold`) so a guest booking here decrements the exact
same Rate Calendar counts a direct-sale or Aggregator hold would, and emits
the same `availability.changed` events -- Service B's cache never drifts
just because the booking came from this channel (mirrors FR-A18's guarantee
for direct sales). `Reservation Hold.channel` is `"website"` here, distinct
from `"direct"` (desk) and `"aggregator"`, purely for reporting/audit.

Guest privacy (NFR-A9 / §5.6) is preserved the same way as everywhere else:
guest contact details live only as `Reservation Guest` child rows, never on
the internal `Guest` DocType.

Every endpoint (read and write) is gated on `Booking Portal Settings.
enabled` via `_guard_portal_enabled` -- disabling the portal in Desk takes
the API down with it, not just the `/book` page (defense in depth: even a
client hitting these methods directly, bypassing the SPA, gets refused).

No payment gateway is wired up -- `create_booking` confirms the reservation
immediately with `payment_reference` set to a fixed "Pay at hotel" marker.
Wiring a real gateway (auth-and-capture before confirming) would replace
just that one step; the hold/inventory/serialization logic around it does
not need to change.
"""
from __future__ import annotations

import json

import frappe

from hotel_erp.api.common import _call_with_deadlock_retry, iso_utc
from hotel_erp.booking.atomic_hold import RoomsUnavailableError, _nights, create_room_hold
from hotel_erp.sync.events import enqueue_availability_changed

_PAYMENT_REFERENCE = "Pay at hotel"


def _as_dict(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def _portal_settings():
    return frappe.get_single("Booking Portal Settings")


def _guard_portal_enabled():
    settings = _portal_settings()
    if not settings.enabled:
        frappe.throw(
            settings.closed_message or "Online booking is temporarily unavailable.",
            frappe.ValidationError,
        )


def _active_property():
    """First Active Property -- same "single storefront" convention the
    Hotel Letterhead fixture already uses (frappe.get_all(..., filters=
    {"status": "Active"}, limit_page_length=1)); this app has no concept of
    guests choosing between multiple properties on one portal yet."""
    rows = frappe.get_all(
        "Property",
        filters={"status": "Active"},
        fields=[
            "property_name",
            "branch_name",
            "address",
            "city",
            "country",
            "star_rating",
            "logo",
            "phone",
            "email",
            "website",
            "tagline",
            "description",
        ],
        limit_page_length=1,
        ignore_permissions=True,
    )
    return rows[0] if rows else None


@frappe.whitelist(allow_guest=True)
def get_portal_settings():
    """Public branding + enabled flag -- drives the portal's header/footer
    and the downloadable ticket's letterhead, and lets the SPA shell decide
    whether to show the booking flow or a closed notice. Deliberately does
    NOT call `_guard_portal_enabled` -- the SPA needs `enabled` and
    `closed_message` precisely when the portal is OFF, to render the closed
    state itself instead of getting a blanket error from every call."""
    settings = _portal_settings()
    return {
        "enabled": bool(settings.enabled),
        "closed_message": settings.closed_message,
        "property": _active_property(),
    }


@frappe.whitelist(allow_guest=True)
def list_room_types():
    """All active room types with gallery/amenities/rate plans, for the
    portal's Rooms page. No date range yet -- see check_availability for
    date-scoped pricing/inventory once the guest picks dates."""
    _guard_portal_enabled()

    room_types = frappe.get_all(
        "Room Type",
        filters={"active": 1},
        fields=[
            "name",
            "code",
            "room_type_name",
            "description",
            "max_occupancy_adults",
            "max_occupancy_children",
            "bed_config",
            "size_sqm",
            "cover_image",
        ],
        order_by="room_type_name asc",
        ignore_permissions=True,
    )

    out = []
    for rt in room_types:
        amenities = frappe.get_all(
            "Room Type Amenity", filters={"parent": rt.name}, fields=["amenity"], order_by="idx", ignore_permissions=True
        )
        photos = frappe.get_all(
            "Room Type Photo",
            filters={"parent": rt.name},
            fields=["image", "caption"],
            order_by="idx",
            ignore_permissions=True,
        )
        rate_plans = frappe.get_all(
            "Rate Plan",
            filters={"room_type": rt.name, "active": 1},
            fields=["code", "plan_name", "base_price_minor", "refundable", "includes_breakfast"],
            order_by="base_price_minor asc",
            ignore_permissions=True,
        )
        out.append(
            {
                "room_type_code": rt.code,
                "name": rt.room_type_name,
                "description": rt.description or "",
                "max_occupancy_adults": rt.max_occupancy_adults,
                "max_occupancy_children": rt.max_occupancy_children or 0,
                "bed_config": rt.bed_config or "",
                "size_sqm": rt.size_sqm,
                "cover_image": rt.cover_image,
                "amenities": [a.amenity for a in amenities],
                "photos": [{"image": p.image, "caption": p.caption} for p in photos],
                "rate_plans": rate_plans,
                "from_price_minor": min((p.base_price_minor for p in rate_plans), default=None),
            }
        )
    return out


@frappe.whitelist(allow_guest=True)
def check_availability(check_in=None, check_out=None, room_type_code=None):
    """Date-scoped price + inventory for every (room type, rate plan) pair,
    same nightly-sum logic as `booking.direct_sale.create_walkin_reservation`
    but read-only (no lock, no decrement) -- purely for the guest's search
    results / room detail page before they commit to a booking."""
    _guard_portal_enabled()

    ci = frappe.utils.getdate(check_in)
    co = frappe.utils.getdate(check_out)
    if not ci or not co or co <= ci:
        frappe.throw("check_out must be after check_in")
    nights = _nights(ci, co)

    filters = {"active": 1}
    if room_type_code:
        filters["code"] = room_type_code
    room_types = frappe.get_all(
        "Room Type",
        filters=filters,
        fields=["name", "code", "room_type_name", "cover_image", "max_occupancy_adults"],
        ignore_permissions=True,
    )

    results = []
    for rt in room_types:
        rate_plans = frappe.get_all(
            "Rate Plan",
            filters={"room_type": rt.name, "active": 1},
            fields=["name", "code", "plan_name", "refundable", "includes_breakfast"],
            ignore_permissions=True,
        )
        for rp in rate_plans:
            rows = frappe.db.sql(
                """
                SELECT date, price_minor, currency, rooms_available
                FROM `tabRate Calendar`
                WHERE rate_plan = %(rp)s AND date IN %(dates)s
                """,
                {"rp": rp.name, "dates": tuple(nights)},
                as_dict=True,
            )
            by_date = {r.date: r for r in rows}
            # A night with no Rate Calendar row at all isn't bookable for this
            # range -- same fail-closed stance as atomic_hold.create_room_hold.
            if any(n not in by_date for n in nights):
                continue
            min_available = min(r.rooms_available for r in by_date.values())
            if min_available <= 0:
                continue
            results.append(
                {
                    "room_type_code": rt.code,
                    "room_type_name": rt.room_type_name,
                    "cover_image": rt.cover_image,
                    "max_occupancy_adults": rt.max_occupancy_adults,
                    "rate_plan_code": rp.code,
                    "rate_plan_name": rp.plan_name,
                    "refundable": bool(rp.refundable),
                    "includes_breakfast": bool(rp.includes_breakfast),
                    "nights": len(nights),
                    "total_amount_minor": sum(by_date[n].price_minor for n in nights),
                    "currency": rows[0].currency,
                    "rooms_available": min_available,
                }
            )
    return results


@frappe.whitelist(allow_guest=True)
def create_booking(
    room_type_code=None,
    rate_plan_code=None,
    check_in=None,
    check_out=None,
    rooms_requested=None,
    guests=None,
    **kwargs,
):
    """Create a confirmed guest self-service reservation. Bare local codes
    (e.g. `DLX-KING`, `FLEX`) -- same as `direct_sale.create_walkin_reservation`,
    this is not an Aggregator call so no `{hotel_slug}.` namespacing applies.

    `guests` is a JSON-or-list of `{name, email, phone}`; the first entry is
    the primary/booking guest and must include a name and email (needed to
    look the booking back up later via `get_booking`, and to send a
    confirmation email in future -- no email is sent yet).
    """
    _guard_portal_enabled()

    room_type_name = frappe.db.get_value("Room Type", {"code": room_type_code, "active": 1}, "name")
    if not room_type_name:
        frappe.throw(f"Unknown room type '{room_type_code}'")
    rate_plan_name = frappe.db.get_value(
        "Rate Plan", {"room_type": room_type_name, "code": rate_plan_code, "active": 1}, "name"
    )
    if not rate_plan_name:
        frappe.throw(f"Unknown rate plan '{rate_plan_code}' for room type '{room_type_code}'")

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
    primary = guest_list[0]
    if not primary.get("name") or not primary.get("email"):
        frappe.throw("The primary guest's name and email are required")

    nights = _nights(ci, co)

    # Atomic multi-night check-and-decrement (NFR-A2) -- same code path every
    # other booking channel uses, so overselling can't happen just because
    # this request came in unauthenticated from the public internet.
    try:
        _call_with_deadlock_retry(create_room_hold, (rate_plan_name, ci, co, rooms), {})
    except RoomsUnavailableError as e:
        frappe.throw(
            "Requested room count is not available for one or more nights: "
            + ", ".join(e.unavailable_dates)
        )

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
            "occupancy": frappe.as_json({}),
            "channel": "website",
            # No Idempotency-Key header from a browser; synthesise a unique
            # key to satisfy the (room_type, idempotency_key) unique index.
            "idempotency_key": f"web-{frappe.generate_hash(length=10)}",
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
            "payment_reference": _PAYMENT_REFERENCE,
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

    # One availability.changed per affected night (§4.7) -- the Aggregator's
    # cache must reflect website-channel bookings too, same as direct sales.
    enqueue_availability_changed(room_type_name, rate_plan_name, ci, co)

    return _public_reservation_dict(reservation, room_type_code, rate_plan_code)


@frappe.whitelist(allow_guest=True)
def get_booking(confirmation_number=None, email=None):
    """Look a booking back up by confirmation number + the primary guest's
    email (the only two things a guest retains after closing the browser
    tab) -- lets the portal re-render the ticket/confirmation page and offer
    the PDF download again later, without any login."""
    _guard_portal_enabled()

    if not confirmation_number or not email:
        frappe.throw("confirmation_number and email are required")

    name = frappe.db.get_value("Reservation", {"confirmation_number": confirmation_number}, "name")
    if not name:
        frappe.throw("Booking not found", frappe.DoesNotExistError)
    reservation = frappe.get_doc("Reservation", name)
    match = any((g.email or "").strip().lower() == email.strip().lower() for g in reservation.guests)
    if not match:
        frappe.throw("Booking not found", frappe.DoesNotExistError)

    room_type_code = frappe.db.get_value("Room Type", reservation.room_type, "code")
    rate_plan_code = frappe.db.get_value("Rate Plan", reservation.rate_plan, "code")
    return _public_reservation_dict(reservation, room_type_code, rate_plan_code)


def _public_reservation_dict(res, room_type_code: str, rate_plan_code: str) -> dict:
    """Local, non-namespaced reservation shape for the guest portal --
    deliberately NOT `hotel_erp.api.serializers.serialize_reservation`,
    which prefixes every id with the Aggregator's `{hotel_slug}.` namespace
    (contract §4.4). A guest booking directly on this site's own portal has
    no Aggregator in the loop, so bare ids/codes are correct here, same
    reasoning as `direct_sale.create_walkin_reservation`."""
    guests = []
    for g in res.guests:
        guest = {"name": g.guest_name}
        if g.phone:
            guest["phone"] = g.phone
        if g.email:
            guest["email"] = g.email
        guests.append(guest)

    room_type_name = frappe.db.get_value("Room Type", res.room_type, "room_type_name")
    rate_plan_name = frappe.db.get_value("Rate Plan", res.rate_plan, "plan_name")

    return {
        "reservation_id": res.name,
        "confirmation_number": res.confirmation_number,
        "room_type_code": room_type_code,
        "room_type_name": room_type_name,
        "rate_plan_code": rate_plan_code,
        "rate_plan_name": rate_plan_name,
        "check_in": str(res.check_in),
        "check_out": str(res.check_out),
        "rooms_requested": res.rooms_requested,
        "status": res.status,
        "guests": guests,
        "total_amount_minor": res.total_amount_minor,
        "currency": res.currency,
        "payment_reference": res.payment_reference,
        # `res.creation` is sometimes a str, sometimes a datetime, depending on
        # how the doc was loaded (confirmed live: a fresh .insert()'s in-memory
        # doc holds it as a plain DB-driver string, not yet cast) -- iso_utc
        # (already used by the /api/v1 serializers for this exact reason)
        # normalises either via frappe.utils.get_datetime first.
        "created_at": iso_utc(res.creation) if res.creation else None,
        "property": _active_property(),
    }
