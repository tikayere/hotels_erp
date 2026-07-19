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
# Fixture record auto-sync (Desk UX layer: Workspaces, Number Cards,
# Dashboard Charts, Kanban Boards, Print Formats, Letter Head)
# ---------------------------------------------------------------------------
# `bench migrate` auto-discovers standard-record fixtures placed at
# <module>/<doctype_folder>/<name>/<name>.json for a fixed list of doctypes
# hardcoded in frappe/model/sync.py's IMPORTABLE_DOCTYPES (DocType, Report,
# Workspace, Print Format, Client Script, ... -- Print Format and Workspace
# are already on that list, which is why those fixtures need no extra wiring
# here). Number Card, Dashboard Chart, Kanban Board, Letter Head and
# Assignment Rule are NOT on that built-in list; this `importable_doctypes`
# hook is the documented Frappe mechanism for extending it so this app's
# fixtures for those doctypes get picked up by `bench migrate` the same way.
importable_doctypes = [
    "Number Card",
    "Dashboard Chart",
    "Kanban Board",
    "Letter Head",
    "Assignment Rule",
]

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

# Authenticates a static `Authorization: Bearer <api_key>` request (contract
# §4.2) as the dedicated "Hotel API" service user. Required because Frappe's
# own request-auth layer intercepts any 2-part Authorization header itself
# (as a native OAuth bearer token or basic/token API key) and raises
# AuthenticationError before before_request hooks run if nothing claims it
# first -- see hotel_erp.api.auth for the full explanation.
auth_hooks = ["hotel_erp.api.auth.validate_bearer_token"]

# ---------------------------------------------------------------------------
# Document lifecycle hooks
# ---------------------------------------------------------------------------
doc_events = {
    "Reservation": {
        "on_update": "hotel_erp.reservation.events.on_reservation_update",
    },
    "Room Type": {
        "after_insert": "hotel_erp.room.events.on_room_type_after_insert",
        "on_update": "hotel_erp.room.events.on_room_type_update",
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
            # Waiting-list watcher — flips `waiting` entries to `notified` and emits
            # waitlist.available once inventory frees up (FR-A5).
            "hotel_erp.booking.waitlist.check_waitlist",
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
        # Dynamic pricing — reprice Rate Calendar rows from each Rate Plan's
        # base_price_minor via its active Pricing Rules, emitting rate.changed
        # for every night whose price moved (FR-A4).
        "hotel_erp.pricing.rules.apply_pricing_rules",
    ],
}
