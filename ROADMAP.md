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

## Implemented, but thinner than the spec describes

- **FR-A4 dynamic pricing** — `Rate Calendar` holds a price per (rate plan,
  night); nothing *sets* that price based on season/occupancy/lead-time
  automatically. Populating it dynamically is a scheduled job someone still
  needs to write.
- **FR-A5 waiting list** — no `Waiting List` DocType; a fully-booked date
  range just returns `409 ROOMS_UNAVAILABLE` today.
- **FR-A7 reception dashboard** — "today's arrivals/departures, late
  checkouts, no-shows" isn't built as a dashboard; the underlying data
  (`Reservation.status`, `check_in`/`check_out`) is all there, just not
  surfaced as a desk page or report yet.
- **FR-A8–A15 internal modules** (Housekeeping, Maintenance, Restaurant,
  Conference, Finance, HR, Inventory, CRM) — DocTypes exist with the fields
  the contract's logical schema (§2.4) calls for, but only as plain
  CRUD — no assignment/scheduling logic (housekeeping task auto-assignment,
  kitchen order routing, payroll calculation, stock consumption tracking,
  night audit, etc.). Matches the spec's own framing of these as
  "internal-only, build per your usual Frappe conventions," but worth
  tracking since "a DocType exists" and "the workflow works" aren't the same
  claim.
- **FR-A16 analytics** — two Query Reports (Hotel Occupancy, ADR/RevPAR),
  not full dashboards.
- **FR-A18 direct/walk-in sales** — `Reservation Hold.channel` supports
  `direct` in the schema, and the atomic-hold/inventory logic doesn't care
  which channel decremented a night, but there's no actual front-desk
  whitelisted method or UI to *create* a direct booking yet — only the
  Aggregator-facing `/api/v1/reservations/hold` path (which always sends
  `channel: aggregator`) is wired up end-to-end.

## Not implemented

- **No automated test suite.** Verification so far has been real,
  end-to-end, against a live stack (concurrent holds, real MariaDB, real
  HMAC-signed webhooks) — but there's no `pytest`/Frappe test-case suite
  checked in, and the CI workflow only builds and pushes the image, it
  doesn't run any tests first. Worth fixing before this is genuinely safe to
  iterate on without a human re-running the manual verification pass every
  time.
- **NFR-A7 backups** — no automated daily snapshot/retention job; purely an
  ops/infra concern deferred to wherever this actually gets deployed.
- Everything in the contract's own **§6 "Open Items for Future Phases"**:
  channel-manager/OTA integration, Event Marketplace, digital
  check-in/smart-lock/IoT, cross-hotel loyalty, corporate booking with
  negotiated rates, multi-currency/multi-country tax handling. These were
  explicitly deferred at the design stage, not accidentally dropped.
