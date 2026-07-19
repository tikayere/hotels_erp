"""Scheduled Sync-layer jobs (registered in hooks.py scheduler_events).

- dispatch_pending_webhooks: delivers due Webhook Outbox rows to the Aggregator,
  applying the contract §4.7 retry backoff.
- emit_heartbeat: enqueues hotel.sync_heartbeat every 5 minutes (§4.7).
- purge_expired_idempotency_records: daily cleanup of records past their 24h TTL
  (§4.10).
"""
from __future__ import annotations

import frappe

from hotel_erp.sync.events import SCHEMA_VERSION, get_hotel_slug
from hotel_erp.sync.webhook_signing import dispatch_webhook_outbox_row

# Contract §4.7 backoff schedule, in seconds: 1m, 5m, 15m, 1h, 6h. Six delivery
# attempts total; after the sixth failure the row is marked 'failed' and the
# Aggregator's reconciliation poller self-heals.
BACKOFF_SECONDS = [60, 300, 900, 3600, 21600]
MAX_ATTEMPTS = 6


def dispatch_pending_webhooks() -> None:
    config = frappe.get_single("Sync Config")
    base_url = config.aggregator_base_url
    secret = config.get_password("aggregator_webhook_secret", raise_exception=False)
    if not base_url or not secret:
        # Not onboarded yet — nothing to deliver to.
        return

    now = frappe.utils.now_datetime()
    rows = frappe.db.sql(
        """
        SELECT name, event_id, event_type, payload, attempts
        FROM `tabWebhook Outbox`
        WHERE status = 'pending'
          AND (next_attempt_at IS NULL OR next_attempt_at <= %(now)s)
        ORDER BY creation
        LIMIT 200
        """,
        {"now": now},
        as_dict=True,
    )
    if not rows:
        return

    import requests

    session = requests.Session()
    for row in rows:
        try:
            ok = dispatch_webhook_outbox_row(session, row, base_url, secret)
        except Exception:
            frappe.log_error(title="Webhook dispatch failed", message=frappe.get_traceback())
            ok = False

        if ok:
            frappe.db.set_value("Webhook Outbox", row.name, "status", "sent", update_modified=False)
        else:
            _schedule_retry(row)
        frappe.db.commit()


def _schedule_retry(row) -> None:
    attempts = (row.attempts or 0) + 1
    if attempts >= MAX_ATTEMPTS:
        frappe.db.set_value(
            "Webhook Outbox",
            row.name,
            {"status": "failed", "attempts": attempts},
            update_modified=False,
        )
        return
    delay = BACKOFF_SECONDS[attempts - 1]
    next_at = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=delay)
    frappe.db.set_value(
        "Webhook Outbox",
        row.name,
        {"attempts": attempts, "next_attempt_at": next_at},
        update_modified=False,
    )


def emit_heartbeat() -> None:
    """hotel.sync_heartbeat every 5 minutes regardless of other activity (§4.7)."""
    slug = get_hotel_slug()
    if not slug:
        return
    import uuid

    event_id = str(uuid.uuid4())
    now = frappe.utils.now_datetime()
    envelope = {
        "event_id": event_id,
        "event_type": "hotel.sync_heartbeat",
        "hotel_id": slug,
        "schema_version": SCHEMA_VERSION,
        "occurred_at": now.isoformat() + "Z",
        "data": {"hotel_id": slug, "server_time": now.isoformat() + "Z"},
    }
    frappe.get_doc(
        {
            "doctype": "Webhook Outbox",
            "event_id": event_id,
            "event_type": "hotel.sync_heartbeat",
            "payload": frappe.as_json(envelope),
            "status": "pending",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()


def purge_expired_idempotency_records() -> None:
    frappe.db.delete("Idempotency Record", {"expires_at": ["<", frappe.utils.now_datetime()]})
    frappe.db.commit()
