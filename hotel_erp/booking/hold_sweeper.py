"""Background job: releases Reservation Hold rows past their expires_at
without a confirm/release call ever arriving (contract section 4.8,
"Failure/edge handling": Service A's hold-expiry sweeper transitions the
hold to `expired` and emits `availability.changed` for every affected night).

Register as a Frappe scheduled job running every minute:
    # hooks.py
    scheduler_events = {
        "cron": {"* * * * *": ["hotel_erp.booking.hold_sweeper.sweep_expired_holds"]}
    }
A 1-minute cron granularity is fine: a hold expiring at T is swept by at
worst T+60s. The Aggregator independently expires its own booking_reference
on the same TTL (contract section 4.8) without waiting on this job.

Unlike the sibling bus project's sweeper, one expired hold here produces
*multiple* availability.changed events -- one per night in the stay,
because the hotel contract's payload is per-(room_type, date, rate_plan)
(section 4.7), not a single schedule-level scalar.

`FOR UPDATE SKIP LOCKED` requires MariaDB >= 10.6 / MySQL >= 8.0. If running
an older server, drop SKIP LOCKED and rely on the cron job never running
concurrently with itself (a single-flight scheduled job is the Frappe
default) instead of on inter-worker lock skipping.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import frappe

from hotel_erp.booking.atomic_hold import release_room_hold


def sweep_expired_holds() -> None:
    expired = frappe.db.sql(
        """
        SELECT name, room_type, rate_plan, check_in, check_out, rooms_requested
        FROM `tabReservation Hold`
        WHERE status = 'held' AND expires_at < %(now)s
        FOR UPDATE SKIP LOCKED
        """,
        {"now": frappe.utils.now_datetime()},
        as_dict=True,
    )
    for hold in expired:
        release_room_hold(hold.rate_plan, hold.check_in, hold.check_out, hold.rooms_requested)
        frappe.db.set_value("Reservation Hold", hold.name, "status", "expired")
        _enqueue_availability_changed(hold.room_type, hold.rate_plan, hold.check_in, hold.check_out)
        # Commit per-hold, not once at the end of the loop: a crash partway
        # through a large sweep batch must not roll back holds already
        # correctly released -- each hold's release is independently durable.
        frappe.db.commit()


def _nights(check_in: date, check_out: date) -> list[date]:
    n = (check_out - check_in).days
    return [check_in + timedelta(days=i) for i in range(n)]


def _enqueue_availability_changed(room_type_id: str, rate_plan_id: str, check_in: date, check_out: date) -> None:
    """Inserts one Webhook Outbox row (doctype_spec.md section 4) per
    affected night for the availability.changed event (contract section
    4.7) -- deliberately one event per (room_type, date, rate_plan), not a
    single event covering the whole stay, matching the per-night shape
    Rate Calendar and the contract's NightlyAvailabilityData both use.
    """
    sync_config = frappe.get_single("Sync Config")
    rate_plan_code, refundable = frappe.db.get_value("Rate Plan", rate_plan_id, ["code", "refundable"])

    rows = frappe.db.sql(
        """
        SELECT date, rooms_available, price_minor, currency
        FROM `tabRate Calendar`
        WHERE rate_plan = %(rate_plan)s AND date IN %(dates)s
        """,
        {"rate_plan": rate_plan_id, "dates": tuple(_nights(check_in, check_out))},
        as_dict=True,
    )

    for row in rows:
        envelope = {
            "event_id": str(uuid.uuid4()),
            "event_type": "availability.changed",
            "hotel_id": sync_config.hotel_slug,
            "schema_version": "1.0",
            "occurred_at": frappe.utils.now_datetime().isoformat() + "Z",
            "data": {
                "room_type_id": f"{sync_config.hotel_slug}.{room_type_id}",
                "date": str(row.date),
                "rate_plan_code": rate_plan_code,
                "rooms_available": row.rooms_available,
                "price_minor": row.price_minor,
                "currency": row.currency,
                "refundable": bool(refundable),
            },
        }
        frappe.get_doc(
            {
                "doctype": "Webhook Outbox",
                "event_id": envelope["event_id"],
                "event_type": envelope["event_type"],
                "payload": frappe.as_json(envelope),
                "status": "pending",
            }
        ).insert(ignore_permissions=True)
