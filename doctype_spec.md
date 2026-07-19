# Hotel ERP — Frappe DocType Specification

Concrete, field-level implementation of the logical schema in `hotels/phase_2_service_contracts.md` §2.4. Every DocType below is buildable directly in Frappe with zero further design decisions. Follows the same conventions as the sibling `bus/erp/doctype_spec.md` — read that file's §1–2 first if you haven't; the money/timestamp/ID rules below are identical in spirit, restated here for completeness.

**App/module layout:** one custom Frappe app, e.g. `hotel_erp`, with modules matching §2.3: `Property`, `Room`, `Reservation`, `Guest`, `Housekeeping`, `Maintenance`, `Restaurant`, `Conference`, `Finance`, `HR`, `Inventory`, `CRM`, `Analytics`, `Sync`.

**Runtime:** `docker-compose.dev.yml` pins `frappe/erpnext:v16.28.0`, which requires **Python 3.14** — a hard requirement of Frappe v16 itself (it uses modern type-alias syntax earlier interpreters can't parse), already satisfied inside that image. Any controller code you write for `hotel_erp` (including the reference modules in `erp/app/`, which are plain, portable Python and already compatible) runs inside that container's Python 3.14 environment, not whatever Python version you have installed on your host.

---

## 1. Three implementation decisions every DocType below depends on

### 1.1 Money — never use Frappe's `Currency` fieldtype for contract amounts

Same rule as bus: every `*_amount_minor` / `*_price_minor` field is fieldtype **`Int`**, storing the exact integer minor-unit value the contract (§4.1 principle 6) requires. Add a computed `Currency`-fieldtype display field separately if a human UI needs one — never compute from it.

### 1.2 Dates and timestamps — pin the site to UTC, and don't confuse the two

- Stay dates (`check_in`, `check_out`, every `rate_calendar` row) are fieldtype **`Date`** — a stay is night-based, not clock-based (§4.1 principle 6). There is no timezone conversion issue here at all; a `Date` is just a calendar date.
- Everything else (`created_at`, `occurred_at`, `updated_at`, hold `expires_at`) is fieldtype **`Datetime`**, and every property's `site_config.json` must set `"time_zone": "UTC"` so the stored value already equals the UTC value the API serializes — no arithmetic at the boundary.

### 1.3 External IDs — store bare local IDs, prefix only at the API/webhook boundary

Identical rule to bus: internally, every DocType's `name` is the bare local ID (e.g. `DLX-KING`, `HOLD-77ab`). The Sync Layer prepends `"{hotel_slug}."` only when serializing to REST responses or webhook payloads, reading `hotel_slug` once from **Sync Config** (§4 below). No other module needs to know a hotel_slug exists.

---

## 2. Frappe fieldtype mapping

Identical table to `bus/erp/doctype_spec.md` §2 — repeated here for a reader who only opens this file:

| Logical type | Frappe fieldtype | Notes |
|---|---|---|
| identifier / short code | `Data`, `unique=1` where it's a business key | |
| free text | `Data` / `Small Text` / `Text Editor` | |
| integer | `Int` | |
| money, minor units | `Int` | never `Currency` — see §1.1 |
| decimal (lat/lon, size) | `Float` | |
| boolean | `Check` | |
| calendar date (no time) | `Date` | stay dates only — see §1.2 |
| UTC timestamp | `Datetime` | see §1.2 |
| enum / status | `Select`, newline-separated, matching the contract enum exactly | |
| foreign key | `Link` | |
| ordered/nested list | `Table` | |
| free-form JSON | `JSON` (Frappe ≥ v14) | `docker-compose.dev.yml` pins `frappe/erpnext:v16.28.0`, comfortably satisfying this |
| currency code | `Data`, `length=3` | ISO-4217 |

---

## 3. DocType field tables

### Property
Autoname: `field:code`.
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| code | Data | unique, reqd — e.g. `downtown`, bare local identifier |
| property_name | Data | reqd |
| branch_name | Data | |
| address | Small Text | |
| city | Data | reqd |
| country | Data | reqd, ISO-3166 alpha-2 |
| lat | Float | |
| lon | Float | |
| star_rating | Int | 1–5 |
| status | Select (`Active\nSuspended`) | reqd, default `Active` |

### Room Type
Autoname: `hash` (see note below).
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| property | Link (Property) | reqd |
| code | Data | reqd — bare `room_type_id` before namespacing (§1.3) |
| room_type_name | Data | reqd |
| description | Text Editor | |
| max_occupancy_adults | Int | reqd |
| max_occupancy_children | Int | default `0` |
| bed_config | Data | |
| size_sqm | Float | |
| amenities | JSON | array of strings |
| photos | JSON | array of URLs (object storage, §2.3) |
| active | Check | default `1` |

**Naming note:** `code` must be unique **per property**, not globally — a Frappe `unique=1` field constraint is global, so this doctype uses `autoname: hash` for the docname and enforces `(property, code)` uniqueness in a `validate()` hook instead. This is the one place hotels genuinely differs from bus (bus routes are unique per company/install, i.e. globally within that DocType, so `field:code` autoname was safe there).

### Room
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| property | Link (Property) | reqd |
| room_type | Link (Room Type) | reqd |
| room_number | Data | reqd |
| floor | Data | |
| status | Select (`available\noccupied\ndirty\nclean\nmaintenance\nout_of_order`) | reqd, default `available` |
| amenities | JSON | array of strings, room-specific overrides/additions to the room type's amenities |

Unique index on `(property, room_number)`.

### Rate Plan
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| room_type | Link (Room Type) | reqd |
| code | Data | reqd — e.g. `FLEX`, unique per room type (validate hook, same pattern as Room Type) |
| plan_name | Data | reqd |
| refundable | Check | default `1` |
| free_cancellation_until_hours_before_checkin | Int | nullable |
| includes_breakfast | Check | default `0` |
| active | Check | default `1` |

### Rate Calendar
Standalone (not a child table) — same reasoning as bus's `Seat Inventory`: the hold flow needs `SELECT ... FOR UPDATE` across N date rows in one transaction, which wants a real table, not a Frappe child table.
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| rate_plan | Link (Rate Plan) | reqd |
| date | Date | reqd |
| price_minor | Int | reqd |
| currency | Data | reqd, length 3 |
| rooms_available | Int | reqd, `>= 0` enforced in the hold transaction, never directly by form validation |

Unique index on `(rate_plan, date)`. **This table is the single source of truth for both pricing and inventory** — populate it far enough in advance (e.g. a rolling 18-month horizon via a scheduled job) that `POST /reservations/hold` never has to fall back to "no row = infinite availability" or "no row = unavailable" ambiguity; a missing row for a requested date must be treated as `0` available, not skipped.

### Reservation Hold
Autoname: `before_insert` hook sets `name = f"HOLD-{frappe.generate_hash(length=6)}"`.
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| room_type | Link (Room Type) | reqd |
| rate_plan | Link (Rate Plan) | reqd |
| check_in | Date | reqd |
| check_out | Date | reqd, `> check_in` |
| rooms_requested | Int | reqd, `>= 1` |
| occupancy | JSON | `{"adults": N, "children": N}` |
| channel | Select (`aggregator\ndirect`) | reqd |
| idempotency_key | Data | unique **per room_type** (composite unique with `room_type`) |
| total_amount_minor | Int | reqd |
| currency | Data | reqd |
| expires_at | Datetime | reqd, UTC |
| status | Select (`held\nconfirmed\nreleased\nexpired`) | reqd, default `held` |

### Reservation
Autoname: naming series `RES-.#####`.
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| hold | Link (Reservation Hold) | reqd, unique |
| confirmation_number | Data | reqd, unique — generated in `before_insert` as `f"{property_abbr}-{name.split('-')[1]}"`, e.g. `SH-1042` |
| room_type | Link (Room Type) | reqd |
| rate_plan | Link (Rate Plan) | reqd |
| check_in | Date | reqd |
| check_out | Date | reqd |
| rooms_requested | Int | reqd |
| guests | Table (Reservation Guest) | reqd, min 1 row |
| total_amount_minor | Int | reqd |
| currency | Data | reqd |
| payment_reference | Data | nullable — set at confirm time |
| status | Select (`confirmed\nchecked_in\nchecked_out\ncancelled\nno_show`) | reqd, default `confirmed` |

### Reservation Guest (child table of Reservation)
Deliberately minimal — see §5.6 of the contract. Full identity documents belong on **Guest** (§ below), never here.
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| guest_name | Data | reqd |
| phone | Data | |
| email | Data | |

### Room Assignment (internal — never exposed externally, §4.1 principle 3)
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| reservation | Link (Reservation) | reqd |
| room | Link (Room) | reqd |
| assigned_at | Datetime | reqd, UTC |

Created by the front-desk/housekeeping workflow at or shortly before `check_in`; setting `reservation.status = checked_in` (which fires the `reservation.checked_in` webhook, §4.7) should require a Room Assignment to exist first.

### Guest (FR-A6 — internal only, NFR-A9/§5.6: never crosses the API boundary)
| fieldname | fieldtype (options) | constraints |
|---|---|---|
| guest_name | Data | reqd |
| passport_no | Data | |
| national_id | Data | |
| phone | Data | |
| email | Data | |
| preferences | JSON | |
| vip_status | Check | default `0` |
| loyalty_points | Int | default `0` |

Enforce this at the code level, not just by convention: the Sync Layer's serializers for every §4.5 response must be built from **Reservation Guest**, never from **Guest** — consider not even granting the API role read-permission on the **Guest** DocType, as a defense-in-depth backstop against an accidental future join.

### Housekeeping Task / Maintenance Request / Restaurant Order / Conference Booking / Finance Txn / Staff / Payroll / Leave

Internal-only (FR-A8–FR-A13) — standard operational DocTypes, not referenced anywhere in §4 (the contract). No external-compatibility constraint on their shape; build per your usual Frappe conventions (Frappe's own HR/Accounting apps cover Finance/HR/Inventory largely out of the box).

---

## 4. Sync Layer DocTypes

Identical pattern to `bus/erp/doctype_spec.md` §4 — **Webhook Outbox**, **Sync Config**, and **Idempotency Record**, field-for-field the same except:

- `Sync Config.company_slug` → `Sync Config.hotel_slug`.
- The outbox's `event_type` values come from the hotel event catalog (§4.7 of this project's contract) instead of the bus one.
- **Idempotency Record** backs `IMPLEMENTATION_GUIDE.md`'s `@idempotent(scope=...)` decorator (contract §4.10) exactly as in the bus project — no differences at all.

Copy that file's three field tables verbatim (only fields, not full DocType JSON, are given for these three in either project) and rename per the bullet above.

---

## 5. Two fully worked DocType JSON files

The two concurrency-critical ones for hotels.

### `hotel_erp/room/doctype/rate_calendar/rate_calendar.json`

```json
{
  "doctype": "DocType",
  "name": "Rate Calendar",
  "module": "Room",
  "custom": 0,
  "istable": 0,
  "autoname": "hash",
  "track_changes": 1,
  "fields": [
    {"fieldname": "rate_plan", "fieldtype": "Link", "options": "Rate Plan", "reqd": 1, "in_list_view": 1},
    {"fieldname": "date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
    {"fieldname": "price_minor", "fieldtype": "Int", "reqd": 1},
    {"fieldname": "currency", "fieldtype": "Data", "reqd": 1, "length": 3},
    {"fieldname": "rooms_available", "fieldtype": "Int", "reqd": 1, "non_negative": 1}
  ],
  "indexes": [
    {"fields": ["rate_plan", "date"], "unique": 1}
  ],
  "permissions": [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "Revenue Manager", "read": 1, "write": 1, "create": 1}
  ]
}
```

### `hotel_erp/reservation/doctype/reservation_hold/reservation_hold.json`

```json
{
  "doctype": "DocType",
  "name": "Reservation Hold",
  "module": "Reservation",
  "custom": 0,
  "istable": 0,
  "autoname": "hash",
  "naming_rule": "Expression (before save)",
  "track_changes": 1,
  "fields": [
    {"fieldname": "room_type", "fieldtype": "Link", "options": "Room Type", "reqd": 1, "in_list_view": 1},
    {"fieldname": "rate_plan", "fieldtype": "Link", "options": "Rate Plan", "reqd": 1},
    {"fieldname": "check_in", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
    {"fieldname": "check_out", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
    {"fieldname": "rooms_requested", "fieldtype": "Int", "reqd": 1},
    {"fieldname": "occupancy", "fieldtype": "JSON"},
    {"fieldname": "channel", "fieldtype": "Select", "options": "aggregator\ndirect", "reqd": 1, "default": "aggregator"},
    {"fieldname": "idempotency_key", "fieldtype": "Data", "reqd": 1},
    {"fieldname": "total_amount_minor", "fieldtype": "Int", "reqd": 1},
    {"fieldname": "currency", "fieldtype": "Data", "reqd": 1, "length": 3},
    {"fieldname": "expires_at", "fieldtype": "Datetime", "reqd": 1, "in_list_view": 1},
    {"fieldname": "status", "fieldtype": "Select", "options": "held\nconfirmed\nreleased\nexpired", "reqd": 1, "default": "held", "in_list_view": 1}
  ],
  "indexes": [
    {"fields": ["room_type", "idempotency_key"], "unique": 1}
  ],
  "permissions": [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "API", "read": 1, "write": 1, "create": 1}
  ]
}
```
The atomic multi-night check-and-reserve logic that goes with this DocType is in `IMPLEMENTATION_GUIDE.md` §"Atomic multi-night room hold" — the hotel analogue of NFR-A2, and the single most important piece of code in this service.
