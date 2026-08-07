"""Internal, session-authenticated API for the hotel_erp Vue frontend (`/pms`,
see `frontend/`). Backs the front-desk operator SPA: dashboard KPIs, the room
board, the reservations list/detail, and the check-in/check-out/cancel
actions.

Unlike `hotel_erp.api.v1` (the external Aggregator-facing REST contract --
bearer-auth, `allow_guest=True`, namespaced `{hotel_slug}.` IDs) every method
here:
  * authenticates with Frappe's own session/role layer, exactly like
    `hotel_erp.booking.direct_sale.create_walkin_reservation` -- a logged-in
    Desk user, never a partner presenting `Authorization: Bearer`;
  * takes and returns BARE local names (Reservation docname, Room docname,
    Room Type `code`), never the Aggregator's `{hotel_slug}.` form;
  * surfaces failures as plain `frappe.throw()` for the SPA's error toast,
    not the contract's §4.9 JSON error envelope.

Mutating actions reuse the same inventory primitives the external contract
and the walk-in-sale flow use (`atomic_hold.release_room_hold`,
`sync.events.enqueue_availability_changed`) so the Aggregator's cache never
drifts just because a booking or cancellation happened from this screen
instead of `/api/v1` (FR-A18).
"""
from __future__ import annotations

import frappe
from frappe.utils import getdate

from hotel_erp.api.common import strip_slug
from hotel_erp.api.pms_common import (
    DESK_ROLES as _DESK_ROLES,
    STAFF_ROLES as _STAFF_ROLES,
    require_desk_role as _require_desk_role,
    require_staff as _require_staff,
    room_types_for_property as _room_types_for_property,
)
from hotel_erp.api import pms_common
from hotel_erp.booking.atomic_hold import _nights, release_room_hold
from hotel_erp.sync.events import enqueue_availability_changed

_OPEN_RESERVATION_STATUSES = ("confirmed", "checked_in")
_ROOM_READY_STATUSES = ("available", "clean")

# Which nav sections `get_boot_info` tells the SPA shell a user may see --
# one entry per module's own role tuple in `pms_common`, so a role added to
# (or removed from) a module there is reflected in the sidebar without a
# second place to update. "reservations" has no entry: every staff role can
# at least read it (see `pms_common.STAFF_ROLES`), so it's unconditional.
_MODULE_ROLES = {
    "housekeeping": pms_common.HOUSEKEEPING_ROLES,
    "maintenance": pms_common.MAINTENANCE_ROLES,
    "restaurant": pms_common.RESTAURANT_ROLES,
    "finance": pms_common.FINANCE_ROLES,
    "hr": pms_common.HR_ROLES,
    "crm": pms_common.CRM_ROLES,
    "conference": pms_common.CONFERENCE_ROLES,
    "inventory": pms_common.INVENTORY_READ_ROLES,
    "revenue": pms_common.REVENUE_ROLES,
}


# ---------------------------------------------------------------------------
# Boot / dashboard
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_boot_info():
    """Current user + role + property list, fetched once on SPA mount."""
    _require_staff()
    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))
    return {
        "user": user,
        "full_name": frappe.utils.get_fullname(user),
        "roles": sorted(user_roles & set(_STAFF_ROLES)),
        "can_manage_bookings": bool(user_roles & set(_DESK_ROLES)),
        # Every module the current user may open at all -- most modules gate
        # individual write actions further (e.g. only a technician role may
        # resolve a Maintenance Request), this is just "show the nav link".
        "modules": sorted(name for name, roles in _MODULE_ROLES.items() if user_roles & set(roles)),
        "properties": frappe.get_all(
            "Property",
            filters={"status": "Active"},
            fields=["name", "property_name", "code"],
            order_by="property_name",
        ),
    }


@frappe.whitelist()
def get_dashboard(property=None):
    _require_staff()
    today = getdate()

    # frappe.db.get_list() rejects a raw `"count(name) as count"` field string
    # (confirmed against a live v16 site while building this -- newer Frappe
    # validates SELECT field strings and only allows aggregates via its dict
    # syntax); plain SQL is simpler here and matches how the rest of this app
    # already does GROUP BY aggregates (see api/v1.py's `_calendar_rows` and
    # booking/atomic_hold.py).
    room_where = "WHERE property = %(property)s" if property else ""
    rooms_by_status = {
        row["status"]: row["count"]
        for row in frappe.db.sql(
            f"SELECT status, COUNT(name) AS count FROM `tabRoom` {room_where} GROUP BY status",
            {"property": property},
            as_dict=True,
        )
    }

    res_filters: dict = {}
    room_types = _room_types_for_property(property)
    if room_types is not None:
        res_filters["room_type"] = ["in", room_types]

    return {
        "date": str(today),
        "arrivals_today": frappe.db.count(
            "Reservation", {**res_filters, "check_in": today, "status": "confirmed"}
        ),
        "departures_today": frappe.db.count(
            "Reservation", {**res_filters, "check_out": today, "status": "checked_in"}
        ),
        "in_house": frappe.db.count("Reservation", {**res_filters, "status": "checked_in"}),
        "rooms_by_status": rooms_by_status,
        "pending_housekeeping_tasks": frappe.db.count(
            "Housekeeping Task", {"status": ["in", ["pending", "in_progress"]]}
        ),
        "open_maintenance_requests": frappe.db.count(
            "Maintenance Request", {"status": ["in", ["open", "assigned", "in_progress"]]}
        ),
    }


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_rooms(property=None, status=None, room_type=None):
    _require_staff()
    filters: dict = {}
    if property:
        filters["property"] = property
    if status:
        filters["status"] = status
    if room_type:
        filters["room_type"] = room_type

    rooms = frappe.get_all(
        "Room",
        filters=filters,
        fields=["name", "property", "room_type", "room_number", "floor", "status"],
        order_by="floor, room_number",
    )
    if not rooms:
        return []

    type_names = {r.room_type for r in rooms}
    type_labels = dict(
        frappe.get_all(
            "Room Type",
            filters={"name": ["in", list(type_names)]},
            fields=["name", "room_type_name"],
            as_list=True,
        )
    )

    occupied = [r.name for r in rooms if r.status == "occupied"]
    guest_by_room: dict = {}
    if occupied:
        rows = frappe.db.sql(
            """
            SELECT ra.room, r.name AS reservation, r.check_out,
                   COALESCE(rg.guest_name, '') AS guest_name
            FROM `tabRoom Assignment` ra
            JOIN `tabReservation` r ON r.name = ra.reservation
            LEFT JOIN `tabReservation Guest` rg ON rg.parent = r.name AND rg.idx = 1
            WHERE ra.room IN %(rooms)s AND r.status = 'checked_in'
            """,
            {"rooms": tuple(occupied)},
            as_dict=True,
        )
        guest_by_room = {row.room: row for row in rows}

    out = []
    for r in rooms:
        entry = {
            "name": r.name,
            "property": r.property,
            "room_type": r.room_type,
            "room_type_name": type_labels.get(r.room_type, r.room_type),
            "room_number": r.room_number,
            "floor": r.floor,
            "status": r.status,
        }
        occ = guest_by_room.get(r.name)
        if occ:
            entry["reservation"] = occ.reservation
            entry["guest_name"] = occ.guest_name
            entry["check_out"] = str(occ.check_out)
        out.append(entry)
    return out


@frappe.whitelist()
def get_room_hierarchy(property=None, status=None):
    """Property -> Floor -> Room Type -> Room, with each room type's cover
    image + full photo gallery attached, for the visual "building map" view
    on Rooms.vue (redesigned so staff can see -- and picture -- the physical
    relationship from building down to room number, not just a flat list).

    A Room itself carries no photo of its own -- two rooms of the same Room
    Type look the same, so pictures live one level up, same place the guest
    booking portal already sources them from (see public_booking.py's
    `list_room_types`, whose Room Type Photo query this mirrors)."""
    _require_staff()
    prop_filters: dict = {"status": "Active"}
    if property:
        prop_filters["name"] = property
    properties = frappe.get_all(
        "Property",
        filters=prop_filters,
        fields=["name", "property_name", "city", "country", "logo"],
        order_by="property_name",
    )
    if not properties:
        return []

    room_filters: dict = {"property": ["in", [p.name for p in properties]]}
    if status:
        room_filters["status"] = status
    rooms = frappe.get_all(
        "Room",
        filters=room_filters,
        fields=["name", "property", "room_type", "room_number", "floor", "status"],
        order_by="floor, room_number",
    )
    if not rooms:
        return [{**p, "floors": [], "room_count": 0} for p in properties]

    type_names = {r.room_type for r in rooms}
    room_types = {
        rt.name: rt
        for rt in frappe.get_all(
            "Room Type",
            filters={"name": ["in", list(type_names)]},
            fields=[
                "name", "code", "room_type_name", "bed_config",
                "max_occupancy_adults", "max_occupancy_children",
                "size_sqm", "cover_image",
            ],
        )
    }
    # Full gallery (image + caption) per room type -- same Room Type Photo
    # child-table query public_booking.py's list_room_types already uses,
    # rather than the derived `photos` JSON field (loses captions).
    photos_by_type: dict = {}
    for row in frappe.get_all(
        "Room Type Photo",
        filters={"parent": ["in", list(type_names)]},
        fields=["parent", "image", "caption"],
        order_by="parent, idx",
    ):
        photos_by_type.setdefault(row.parent, []).append({"image": row.image, "caption": row.caption})

    occupied = [r.name for r in rooms if r.status == "occupied"]
    guest_by_room: dict = {}
    if occupied:
        occ_rows = frappe.db.sql(
            """
            SELECT ra.room, r.name AS reservation, r.check_out,
                   COALESCE(rg.guest_name, '') AS guest_name
            FROM `tabRoom Assignment` ra
            JOIN `tabReservation` r ON r.name = ra.reservation
            LEFT JOIN `tabReservation Guest` rg ON rg.parent = r.name AND rg.idx = 1
            WHERE ra.room IN %(rooms)s AND r.status = 'checked_in'
            """,
            {"rooms": tuple(occupied)},
            as_dict=True,
        )
        guest_by_room = {row.room: row for row in occ_rows}

    # property -> floor -> room_type -> [room entry]
    tree: dict = {}
    for r in rooms:
        floor_bucket = tree.setdefault(r.property, {}).setdefault(r.floor or None, {})
        entry = {"name": r.name, "room_number": r.room_number, "status": r.status}
        occ = guest_by_room.get(r.name)
        if occ:
            entry["reservation"] = occ.reservation
            entry["guest_name"] = occ.guest_name
            entry["check_out"] = str(occ.check_out)
        floor_bucket.setdefault(r.room_type, []).append(entry)

    def _floor_sort_key(floor):
        # Numeric floors sort numerically ("2" before "10"); non-numeric
        # ("Ground", "Mezzanine") sort after them alphabetically; unassigned
        # (None) always last.
        if floor is None:
            return (2, "", 0)
        try:
            return (0, "", int(floor))
        except ValueError:
            return (1, floor, 0)

    out = []
    for p in properties:
        prop_bucket = tree.get(p.name, {})
        floors = []
        for floor_key in sorted(prop_bucket.keys(), key=_floor_sort_key):
            type_bucket = prop_bucket[floor_key]
            room_types_out = []
            for rt_name, room_list in type_bucket.items():
                rt = room_types.get(rt_name) or {}
                room_types_out.append({
                    "room_type": rt_name,
                    "room_type_name": rt.get("room_type_name", rt_name),
                    "code": rt.get("code"),
                    "bed_config": rt.get("bed_config"),
                    "max_occupancy_adults": rt.get("max_occupancy_adults"),
                    "max_occupancy_children": rt.get("max_occupancy_children"),
                    "size_sqm": rt.get("size_sqm"),
                    "cover_image": rt.get("cover_image"),
                    "photos": photos_by_type.get(rt_name, []),
                    "rooms": sorted(room_list, key=lambda x: x["room_number"]),
                })
            room_types_out.sort(key=lambda rt: rt["room_type_name"])
            floors.append({
                "floor": floor_key,
                "room_types": room_types_out,
                "room_count": sum(len(rt["rooms"]) for rt in room_types_out),
            })
        out.append({
            "property": p.name,
            "property_name": p.property_name,
            "city": p.city,
            "country": p.country,
            "logo": p.logo,
            "floors": floors,
            "room_count": sum(f["room_count"] for f in floors),
        })
    return out


@frappe.whitelist()
def list_available_rooms(reservation):
    """Rooms eligible to be assigned when checking `reservation` in --
    matching room type/property, and currently ready (`available`/`clean`)."""
    _require_staff()
    res = frappe.get_doc("Reservation", reservation)
    room_type = frappe.get_doc("Room Type", res.room_type)
    return frappe.get_all(
        "Room",
        filters={
            "room_type": res.room_type,
            "property": room_type.property,
            "status": ["in", _ROOM_READY_STATUSES],
        },
        fields=["name", "room_number", "floor", "status"],
        order_by="floor, room_number",
    )


# ---------------------------------------------------------------------------
# Room types / rate plans / availability preview (for the New Reservation form)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_room_types(property=None):
    _require_staff()
    filters = {"active": 1}
    if property:
        filters["property"] = property
    room_types = frappe.get_all(
        "Room Type",
        filters=filters,
        fields=[
            "name",
            "property",
            "code",
            "room_type_name",
            "max_occupancy_adults",
            "max_occupancy_children",
            "bed_config",
        ],
        order_by="room_type_name",
    )
    if not room_types:
        return []
    plans = frappe.get_all(
        "Rate Plan",
        filters={"room_type": ["in", [rt.name for rt in room_types]], "active": 1},
        fields=[
            "name",
            "room_type",
            "code",
            "plan_name",
            "refundable",
            "includes_breakfast",
            "base_price_minor",
        ],
        order_by="plan_name",
    )
    plans_by_type: dict = {}
    for p in plans:
        plans_by_type.setdefault(p.room_type, []).append(p)
    for rt in room_types:
        rt["rate_plans"] = plans_by_type.get(rt.name, [])
    return room_types


@frappe.whitelist()
def get_availability(rate_plan, check_in, check_out):
    """Read-only nightly price/availability preview -- no row locks, no
    inventory decrement (that only happens on actual submit, via
    `booking.direct_sale.create_walkin_reservation`)."""
    _require_staff()
    ci, co = getdate(check_in), getdate(check_out)
    if co <= ci:
        frappe.throw("check_out must be after check_in")
    nights = _nights(ci, co)

    rows = frappe.db.sql(
        """
        SELECT date, price_minor, currency, rooms_available
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan, "dates": tuple(nights)},
        as_dict=True,
    )
    by_date = {r.date: r for r in rows}

    nightly = [
        {
            "date": str(n),
            "price_minor": by_date[n].price_minor if n in by_date else None,
            "rooms_available": by_date[n].rooms_available if n in by_date else 0,
        }
        for n in nights
    ]
    currency = next((r.currency for r in rows), "")
    return {
        "nights": nightly,
        "min_rooms_available": min((row["rooms_available"] for row in nightly), default=0),
        "total_amount_minor": sum(row["price_minor"] or 0 for row in nightly),
        "currency": currency,
    }


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------
@frappe.whitelist()
def create_walkin_reservation(**kwargs):
    """Thin reshape of `booking.direct_sale.create_walkin_reservation` for
    this SPA: same auth, same atomic-hold/inventory/event side effects --
    only the response shape differs. That function's return value is built
    by `serialize_reservation`, the Aggregator-contract serializer, whose
    `reservation_id` is namespaced (`"{hotel_slug}.RES-00001"`); every other
    method here (`get_reservation`, `check_in_reservation`, ...) instead
    returns/accepts the BARE Reservation docname, so this strips the
    namespace and re-fetches through `get_reservation` for a consistent
    shape rather than making the SPA carry two different ID conventions.
    """
    from hotel_erp.booking.direct_sale import create_walkin_reservation as _create_walkin

    result = _create_walkin(**kwargs)
    return get_reservation(strip_slug(result["reservation_id"]))


@frappe.whitelist()
def list_reservations(status=None, search=None, property=None, arrivals_on=None, page=1, page_length=20):
    _require_staff()
    page = max(1, int(page or 1))
    page_length = min(100, max(1, int(page_length or 20)))

    conditions = ["1=1"]
    values: dict = {}

    if status:
        conditions.append("r.status = %(status)s")
        values["status"] = status
    if arrivals_on:
        conditions.append("r.check_in = %(arrivals_on)s")
        values["arrivals_on"] = getdate(arrivals_on)
    room_types = _room_types_for_property(property)
    if room_types is not None:
        conditions.append("r.room_type IN %(room_types)s")
        values["room_types"] = tuple(room_types) or ("",)
    if search:
        conditions.append(
            "(r.name LIKE %(search)s OR r.confirmation_number LIKE %(search)s "
            "OR EXISTS (SELECT 1 FROM `tabReservation Guest` rg "
            "WHERE rg.parent = r.name AND rg.guest_name LIKE %(search)s))"
        )
        values["search"] = f"%{search}%"

    where = " AND ".join(conditions)
    total_count = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabReservation` r WHERE {where}", values
    )[0][0]

    rows = frappe.db.sql(
        f"""
        SELECT r.name, r.confirmation_number, r.room_type, rt.room_type_name,
               r.check_in, r.check_out, r.rooms_requested, r.status,
               r.total_amount_minor, r.currency,
               COALESCE(rg.guest_name, '') AS guest_name
        FROM `tabReservation` r
        LEFT JOIN `tabRoom Type` rt ON rt.name = r.room_type
        LEFT JOIN `tabReservation Guest` rg ON rg.parent = r.name AND rg.idx = 1
        WHERE {where}
        ORDER BY r.check_in DESC, r.name DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**values, "limit": page_length, "offset": (page - 1) * page_length},
        as_dict=True,
    )
    for r in rows:
        r.check_in = str(r.check_in)
        r.check_out = str(r.check_out)

    return {"data": rows, "total_count": total_count, "page": page, "page_length": page_length}


@frappe.whitelist()
def get_reservation(name):
    _require_staff()
    res = frappe.get_doc("Reservation", name)
    room_type = frappe.get_doc("Room Type", res.room_type)
    rate_plan = frappe.get_doc("Rate Plan", res.rate_plan) if res.rate_plan else None
    assignment = frappe.db.get_value(
        "Room Assignment", {"reservation": res.name}, ["name", "room", "assigned_at"], as_dict=True
    )

    out = {
        "name": res.name,
        "confirmation_number": res.confirmation_number,
        "status": res.status,
        "check_in": str(res.check_in),
        "check_out": str(res.check_out),
        "rooms_requested": res.rooms_requested,
        "total_amount_minor": res.total_amount_minor,
        "currency": res.currency,
        "payment_reference": res.payment_reference,
        "created_at": frappe.utils.get_datetime_str(res.creation),
        "room_type": {"name": room_type.name, "code": room_type.code, "room_type_name": room_type.room_type_name},
        "rate_plan": {"name": rate_plan.name, "code": rate_plan.code, "plan_name": rate_plan.plan_name}
        if rate_plan
        else None,
        "guests": [
            {"guest_name": g.guest_name, "phone": g.phone, "email": g.email} for g in res.guests
        ],
        "room_assignment": dict(assignment) if assignment else None,
    }
    if assignment:
        out["room_assignment"]["assigned_at"] = frappe.utils.get_datetime_str(assignment.assigned_at)
    return out


@frappe.whitelist()
def check_in_reservation(reservation, room):
    _require_desk_role()
    res = frappe.get_doc("Reservation", reservation)
    if res.status != "confirmed":
        frappe.throw(f"Only a confirmed reservation can be checked in (current status: {res.status})")

    room_doc = frappe.get_doc("Room", room)
    if room_doc.room_type != res.room_type:
        frappe.throw("Selected room does not match the reservation's room type")
    if room_doc.status not in _ROOM_READY_STATUSES:
        frappe.throw(f"Room {room_doc.room_number} is not ready for check-in (status: {room_doc.status})")
    if frappe.db.exists("Room Assignment", {"reservation": res.name}):
        frappe.throw("This reservation already has a room assigned")

    frappe.get_doc(
        {"doctype": "Room Assignment", "reservation": res.name, "room": room_doc.name}
    ).insert(ignore_permissions=True)
    frappe.db.set_value("Room", room_doc.name, "status", "occupied")

    res.status = "checked_in"
    res.save(ignore_permissions=True)  # doc_events.on_reservation_update fires the webhook
    return get_reservation(res.name)


@frappe.whitelist()
def check_out_reservation(reservation):
    _require_desk_role()
    res = frappe.get_doc("Reservation", reservation)
    if res.status != "checked_in":
        frappe.throw(f"Only a checked-in reservation can be checked out (current status: {res.status})")

    res.status = "checked_out"
    res.save(ignore_permissions=True)  # on_reservation_update creates the housekeeping task + sets room dirty
    return get_reservation(res.name)


@frappe.whitelist()
def cancel_reservation(reservation, reason=None):
    _require_desk_role()
    res = frappe.get_doc("Reservation", reservation)
    if res.status not in ("confirmed",):
        frappe.throw(f"A {res.status} reservation cannot be cancelled from this screen")

    release_room_hold(res.rate_plan, res.check_in, res.check_out, res.rooms_requested)
    res.status = "cancelled"
    res.save(ignore_permissions=True)
    enqueue_availability_changed(res.room_type, res.rate_plan, res.check_in, res.check_out)
    if reason:
        res.add_comment("Comment", f"Cancelled from Front Desk: {reason}")
    return get_reservation(res.name)
