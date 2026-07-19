# hotel_erp — Implementation status

Tracks what's actually built vs. what `phase_1.md`/`phase_2_service_contracts.md`
call for but this repo doesn't do yet. Written from the implementation and
verification work itself, not from a spec review — every "not implemented"
line below was confirmed by checking the actual code, not assumed absent.

## Fully implemented and verified

Everything in **contract §4** (the wire boundary with the Aggregator):
all 9 `/api/v1/*` endpoints, atomic multi-night hold/release, idempotency
(`Idempotency-Key` replay + conflict detection), the guest-privacy
permission boundary, the webhook outbox + dispatcher + scheduler/worker
pipeline, and bearer authentication. Verified end-to-end against a real
running stack, including concurrent-hold correctness under real MariaDB
lock contention (not just unit tests) — see the sibling `hotels` project's
git history for the two real bugs that surfaced there and how they were
fixed (`frappe.QueryDeadlockError` retry, and `auth_hooks` wiring).

- **FR-A18 direct/walk-in sales** — `hotel_erp.booking.direct_sale.create_walkin_reservation`,
  a `@frappe.whitelist()` method authenticated by Frappe's own session/role
  layer (`Hotel Front Desk`/`Revenue Manager`/`System Manager`), not the
  Aggregator's bearer scheme. Reuses the same `atomic_hold` decrement and
  emits the same `availability.changed` events. Verified live: correct
  inventory decrement, and a Guest-role (unauthenticated) session correctly
  gets `403`.
- **FR-A5 waiting list** — `Waiting List Entry` DocType, `POST
  /api/v1/reservations/waitlist`, and a 1-minute `check_waitlist` scheduled
  job that flips entries to `notified` and emits `waitlist.available`
  (IDs/dates only, no contact info on the wire) once a stay's every night
  has enough rooms again. Verified live end-to-end including the Aggregator
  side picking the event up correctly (see `hotels_aggregator/ROADMAP.md` —
  this surfaced a real forward-compatibility bug there, now fixed).
- **FR-A4 dynamic pricing** — `Pricing Rule` DocType (season/holiday/
  day-of-week/lead-time/occupancy, percentage or fixed adjustment, composed
  in priority order) + a daily `apply_pricing_rules` job repricing existing
  `Rate Calendar` rows from each Rate Plan's `base_price_minor` and emitting
  `rate.changed` for nights that actually moved. Verified live: a
  day-of-week weekend-surge rule correctly repriced only Saturday/Sunday
  nights, left every other night untouched, and the resulting price landed
  correctly in the Aggregator's index via the real webhook path.
- **FR-A7 reception dashboard** — four Query Reports (Today's Arrivals,
  Today's Departures, Late Checkouts, Arrivals Not Checked In) under
  Analytics, granted to `Hotel Front Desk` too (the other reports are
  `System Manager`-only). Verified live with real reservation data,
  including the Late Checkouts boundary condition (`check_out < today`,
  not `<= today`) actually excluding a same-day checkout correctly.
- **Frappe-native Desk UX** — 7 role-oriented Workspaces (Front Desk,
  Housekeeping, Maintenance, Revenue Management, Finance, HR, and a Hotel
  Management overview), 4 Number Cards + 1 Dashboard Chart, 2 Kanban Boards
  (Housekeeping Task, Maintenance Request), 2 Print Formats (Reservation
  Confirmation, Reservation Folio) + a Letter Head, and 2 disabled
  Assignment Rule templates (need real staff populated before enabling —
  shipping them pre-enabled with no real users would auto-assign nothing
  usefully and is a worse default than an explicit opt-in). New
  `Maintenance Staff`/`Finance Manager` roles, since Maintenance Request and
  Finance Txn previously had no dedicated non-admin role to grant workspace
  access to. Print formats verified live: correct confirmation number,
  correct guest name (from `Reservation.guests` only, never the `Guest`
  DocType), correct money formatting (minor units ÷ 100), no PII leakage.
- **Report/export/print permission flags across every DocType** — every
  permission row previously only set `read`/`write`/`create`/`delete`; the
  separate `report` flag (which actually gates whether a role's reports on
  that doctype are listed as navigable in the Desk UI) was never set
  anywhere. This is why reports could appear inaccessible even to
  Administrator when browsing the Desk normally, despite direct API
  execution always working (Administrator's runtime bypass masks the gap
  that a role-based user hits for real) — confirmed by directly comparing
  `frappe.has_permission(doctype, "report")` for Administrator vs. a
  `Hotel Front Desk` test user before and after the fix.
- **Two-pass fixture sync bug, found and fixed** — `bench install-app`'s
  own single process does not reliably sync fixture records for doctypes
  registered via `hooks.py`'s `importable_doctypes` hook (Kanban Board,
  Letter Head, Assignment Rule — confirmed reproducible on a genuinely
  fresh site: zero rows after `install-app`, correct rows after an
  immediately-following `bench migrate` in a fresh process). Looks like a
  controller-cache ordering quirk internal to Frappe, not a mistake in the
  fixture files themselves. Worked around in both `docker-compose.dev.yml`
  and `docker-compose.prod.yml` by running `migrate` again right after
  `install-app` for both sites — confirmed this actually closes the gap on
  a from-scratch `docker compose down -v && up -d`, not just asserted.

## Implemented, but thinner than the spec describes

- **FR-A8–A15 internal modules** (Housekeeping, Maintenance, Restaurant,
  Conference, Finance, HR, Inventory, CRM) — DocTypes exist with the fields
  the contract's logical schema (§2.4) calls for, but only as plain
  CRUD — no assignment/scheduling logic (housekeeping task auto-assignment,
  kitchen order routing, payroll calculation, stock consumption tracking,
  night audit, etc.). Matches the spec's own framing of these as
  "internal-only, build per your usual Frappe conventions," but worth
  tracking since "a DocType exists" and "the workflow works" aren't the same
  claim.
- **FR-A16 analytics** — the occupancy/ADR/RevPAR/reception reports above
  are Query Reports, not full dashboards.

## Not implemented

- **No automated test suite.** Verification so far has been real,
  end-to-end, against a live stack (concurrent holds, real MariaDB, real
  HMAC-signed webhooks, real dynamic-pricing/waitlist runs) — but there's no
  `pytest`/Frappe test-case suite checked in, and the CI workflow only
  builds and pushes the image, it doesn't run any tests first. Worth fixing
  before this is genuinely safe to iterate on without a human re-running the
  manual verification pass every time.
- **NFR-A7 backups** — no automated daily snapshot/retention job; purely an
  ops/infra concern deferred to wherever this actually gets deployed.
- Everything in the contract's own **§6 "Open Items for Future Phases"**:
  channel-manager/OTA integration, Event Marketplace, digital
  check-in/smart-lock/IoT, cross-hotel loyalty, corporate booking with
  negotiated rates, multi-currency/multi-country tax handling. These were
  explicitly deferred at the design stage, not accidentally dropped.
