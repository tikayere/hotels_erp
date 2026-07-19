"""HMAC-SHA256 signing for outbound webhooks (contract section 4.2).

Used by the Webhook Dispatcher (hotels/phase_2_service_contracts.md section
2.3) when POSTing to the Aggregator's fixed webhook URL. Reads the shared
secret from Sync Config (hotels/erp/doctype_spec.md section 4) -- never
hardcode it, never log it. Logic is identical to the sibling bus project's
version; only the header names differ (X-Hotel-* here vs X-Bus-* there).
"""
from __future__ import annotations

import hashlib
import hmac
import time


def sign_webhook_body(secret: str, raw_body: bytes, timestamp: int | None = None) -> tuple[str, int]:
    """Returns (signature_header_value, timestamp).

    signature_header_value already has the "sha256=" prefix the contract
    requires (section 4.2) -- set it on X-Hotel-Signature verbatim; set
    X-Hotel-Timestamp to the returned timestamp.
    """
    ts = timestamp if timestamp is not None else int(time.time())
    message = f"{ts}.".encode() + raw_body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}", ts


def dispatch_webhook_outbox_row(session, row, aggregator_base_url: str, webhook_secret: str) -> bool:
    """Delivers one Webhook Outbox row (doctype_spec.md section 4). Returns
    True on 2xx (caller marks the row 'sent'), False otherwise (caller
    increments attempts and schedules the next retry per contract section
    4.7's backoff: 1m, 5m, 15m, 1h, 6h).
    """
    raw_body = row.payload.encode() if isinstance(row.payload, str) else row.payload
    signature, timestamp = sign_webhook_body(webhook_secret, raw_body)

    response = session.post(
        f"{aggregator_base_url}/api/v1/webhooks/events",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hotel-Signature": signature,
            "X-Hotel-Timestamp": str(timestamp),
        },
        timeout=10,
    )
    return 200 <= response.status_code < 300
