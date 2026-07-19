# hotel_erp — Service A of the Hotel Ecosystem

A Frappe app implementing the **Hotel ERP/PMS** side of a two-service hotel
booking ecosystem. One installation of this app runs per hotel property; it
is the system of record for that hotel's rooms, rates, reservations, guests,
and internal operations, and stays fully operable with zero connectivity to
the central marketplace (Service B, [hotels_aggregator](https://github.com/tikayere/hotels_aggregator)).

The full design — requirements, architecture, database schema, and **the
wire contract** this app and the Aggregator both honor — lives in the
sibling `hotels` project's `phase_2_service_contracts.md` and
`IMPLEMENTATION_GUIDE.md`. This repo is the implementation of that
contract's Service A side; read those documents first if you're touching
anything under `hotel_erp/api/` or `hotel_erp/sync/`, since changes there
are changes to a boundary both services depend on.

See [`ROADMAP.md`](ROADMAP.md) for what's implemented vs. what's still open.

## What's here

| Path | What it is |
|---|---|
| `hotel_erp/property/`, `room/`, `reservation/`, `guest/` | Contract-critical DocTypes: Property, Room Type, Room, Rate Plan, Rate Calendar, Reservation Hold, Reservation, Reservation Guest, Room Assignment, Guest. |
| `hotel_erp/booking/atomic_hold.py` | The multi-night room-hold concurrency logic — locks every affected night's `Rate Calendar` row, checks all of them before decrementing any, so a hold either succeeds in full or fails without touching inventory. |
| `hotel_erp/booking/hold_sweeper.py` | Scheduled job releasing holds past `expires_at`, emitting one `availability.changed` event per affected night. |
| `hotel_erp/sync/` | The transactional webhook outbox, HMAC signing, idempotency handling, and the dispatcher that delivers events to the Aggregator. |
| `hotel_erp/api/` | The `/api/v1/*` REST surface (health, room-types, availability, reservations hold/confirm/release/cancel), custom routing on top of Frappe's method dispatch, and the bearer-auth hook. |
| `hotel_erp/housekeeping/`, `maintenance/`, `restaurant/`, `conference/`, `finance/`, `hr/`, `inventory/`, `crm/`, `analytics/` | Internal-only operational modules — never exposed across the API boundary. |
| `Dockerfile` | Bakes this app into `frappe/erpnext:v16.28.0` (and strips `erpnext` itself out — see the file's own comments for why). Published to Docker Hub by `.github/workflows/docker-publish.yml` on every push to `main`. |

## Guest privacy (read this before touching anything guest-related)

Passport numbers and national IDs live only on the `Guest` DocType, which
the API-facing role (`Hotel API`) has **no read permission on** — enforced
at the Frappe permission layer, not by convention. Every `/api/v1/*`
response that includes guest data builds it from `Reservation Guest`
(name/phone/email only). If you're adding a new endpoint that touches
guests, verify `frappe.has_permission("Guest", "read")` is still `False` for
the `Hotel API` role before you consider the change done.

## Running it

The full two-service stack (this app + the Aggregator + all datastores) is
defined in the sibling `hotels` project's `docker-compose.dev.yml` (builds
this repo from source) and `docker-compose.prod.yml` (pulls the published
Docker Hub image) — start there. To run just this app standalone against
that compose file's Frappe bench:

```bash
docker compose -f docker-compose.dev.yml up -d
curl -H "Host: hotel-alpha.localhost" http://localhost:8001/api/v1/health
```

To build and sanity-check the image on its own:

```bash
docker build -t hotel_erp:local .
docker run --rm hotel_erp:local bash -c 'env/bin/python -c "import hotel_erp"'
```

## Development notes

- **Money** is always an integer in minor currency units (never a float) —
  every `*_price_minor` / `*_amount_minor` field is Frappe fieldtype `Int`,
  never `Currency`.
- **Stay dates** (`check_in`/`check_out`, every `Rate Calendar` row) are
  fieldtype `Date`; everything else timestamped is `Datetime`, and every
  site is pinned to UTC — there is no timezone conversion at the API
  boundary.
- **External IDs are namespaced only at the boundary**: internally every
  DocType's `name` is a bare local ID; `hotel_erp/sync/events.py` prepends
  `"{hotel_slug}."` only when serializing to a REST response or webhook
  payload.
- If you change `atomic_hold.py` or `webhook_signing.py`, re-verify against
  concurrent load before trusting the change — both have already surfaced
  real bugs under real MariaDB contention that unit-level testing alone
  didn't catch (see `ROADMAP.md` / git history for specifics).
