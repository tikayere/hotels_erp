app_name = "hotel_erp"
app_title = "Hotel ERP"
app_publisher = "Hotel ERP Team"
app_description = "Hotel ERP / PMS — Service A of the hotel booking ecosystem"
app_email = "pourou.2000@gmail.com"
app_license = "MIT"
app_version = "1.0.0"

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
after_install = "hotel_erp.setup.install.after_install"

# ---------------------------------------------------------------------------
# Request routing
# ---------------------------------------------------------------------------
# The external contract (phase_2 §4.5) serves clean REST paths under /api/v1/*
# (e.g. GET /api/v1/health, POST /api/v1/reservations/hold). Frappe's native
# dispatch only understands /api/method/<dotted.path> and /api/resource/<dt>,
# so `route_v1` (a before_request hook) parses the /api/v1/* path, injects the
# path/query params into frappe.local.form_dict and points form_dict.cmd at the
# matching whitelisted method in hotel_erp.api.v1. `unwrap_v1` (after_request)
# then lifts the method's return value out of Frappe's default {"message": ...}
# envelope so the HTTP body matches the OpenAPI schema shape exactly.
before_request = ["hotel_erp.api.router.route_v1"]
after_request = ["hotel_erp.api.router.unwrap_v1"]

# ---------------------------------------------------------------------------
# Document lifecycle hooks
# ---------------------------------------------------------------------------
doc_events = {
    "Reservation": {
        "on_update": "hotel_erp.reservation.events.on_reservation_update",
    },
}

# ---------------------------------------------------------------------------
# Scheduled background jobs
# ---------------------------------------------------------------------------
scheduler_events = {
    "cron": {
        # Hold-expiry sweeper — releases inventory for holds past expires_at and
        # emits one availability.changed event per affected night (contract §4.8).
        "* * * * *": [
            "hotel_erp.booking.hold_sweeper.sweep_expired_holds",
            # Webhook Outbox dispatcher — delivers pending/retry-due rows with the
            # contract §4.7 backoff (1m, 5m, 15m, 1h, 6h; 6 attempts then failed).
            "hotel_erp.sync.dispatcher.dispatch_pending_webhooks",
        ],
        # hotel.sync_heartbeat — emitted every 5 minutes regardless of activity
        # (contract §4.7).
        "*/5 * * * *": [
            "hotel_erp.sync.dispatcher.emit_heartbeat",
        ],
    },
    "daily": [
        # Purge Idempotency Records past their 24h expiry (contract §4.10).
        "hotel_erp.sync.dispatcher.purge_expired_idempotency_records",
    ],
}
