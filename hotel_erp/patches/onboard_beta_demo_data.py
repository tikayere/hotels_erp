"""One-off script: seed hotel-beta with enough real data (Property, Room
Type, Rate Plan, Rate Calendar) to actually be a second hotel in the
marketplace, instead of an empty shell no one can search or book.
Run via: bench --site hotel-beta.localhost execute hotel_erp.patches.onboard_beta_demo_data.execute
"""
from __future__ import annotations

import datetime

import frappe


def execute():
    if not frappe.db.exists("Property", "beach-resort"):
        frappe.get_doc({
            "doctype": "Property",
            "code": "beach-resort",
            "property_name": "Coral Beach Resort",
            "branch_name": "Main",
            "city": "Zanzibar City",
            "country": "TZ",
            "star_rating": 4,
            "status": "Active",
        }).insert(ignore_permissions=True)

    if not frappe.db.exists("Room Type", {"property": "beach-resort", "code": "DLX-SEA"}):
        room_type = frappe.get_doc({
            "doctype": "Room Type",
            "property": "beach-resort",
            "code": "DLX-SEA",
            "room_type_name": "Deluxe Sea View",
            "description": "Sea-facing room with private balcony and king bed.",
            "max_occupancy_adults": 2,
            "max_occupancy_children": 1,
            "bed_config": "1 King",
            "size_sqm": 30,
            "active": 1,
        })
        room_type.insert(ignore_permissions=True)
        room_type_id = room_type.name
    else:
        room_type_id = frappe.db.get_value("Room Type", {"property": "beach-resort", "code": "DLX-SEA"}, "name")

    if not frappe.db.exists("Room", {"property": "beach-resort", "room_number": "101"}):
        frappe.get_doc({
            "doctype": "Room",
            "property": "beach-resort",
            "room_type": room_type_id,
            "room_number": "101",
            "floor": "1",
            "status": "available",
        }).insert(ignore_permissions=True)

    if not frappe.db.exists("Rate Plan", {"room_type": room_type_id, "code": "FLEX"}):
        rate_plan = frappe.get_doc({
            "doctype": "Rate Plan",
            "room_type": room_type_id,
            "code": "FLEX",
            "plan_name": "Flexible Rate",
            "refundable": 1,
            "free_cancellation_until_hours_before_checkin": 24,
            "includes_breakfast": 1,
            "base_price_minor": 18000,  # $180.00
            "active": 1,
        })
        rate_plan.insert(ignore_permissions=True)
        rate_plan_id = rate_plan.name
    else:
        rate_plan_id = frappe.db.get_value("Rate Plan", {"room_type": room_type_id, "code": "FLEX"}, "name")

    today = datetime.date.today()
    created = 0
    # 400 days: wide enough for the integration suite (tests/test_concurrency.py,
    # tests/test_guest_privacy.py) to use far-future dates it can safely own
    # without colliding with real bookings, without needing to keep this in
    # lockstep with whatever offsets those tests happen to use.
    for i in range(400):
        d = today + datetime.timedelta(days=i)
        if not frappe.db.exists("Rate Calendar", {"rate_plan": rate_plan_id, "date": d}):
            frappe.get_doc({
                "doctype": "Rate Calendar",
                "rate_plan": rate_plan_id,
                "date": d,
                "price_minor": 18000,
                "currency": "USD",
                "rooms_available": 3,
            }).insert(ignore_permissions=True)
            created += 1

    frappe.db.commit()
    print(f"OK property=beach-resort room_type={room_type_id} rate_plan={rate_plan_id} rate_calendar_rows_created={created}")
