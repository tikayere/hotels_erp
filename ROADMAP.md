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
- **Desk UI "infinite loop" reported by a real user, root-caused and fixed** —
  browsing `/desk` looked stuck/looping; nginx access logs from the actual
  browser session showed a `GET /socket.io/*` polling request repeating
  every few seconds with growing intervals, every single one a `502`. Root
  cause: this dev topology's `erp-nginx` never had a `SOCKETIO` target
  configured, defaulting to an unreachable `0.0.0.0:9000` — there was no
  websocket service at all, a gap deliberately accepted early on since
  nothing in the REST contract needs realtime push. That reasoning stopped
  holding once the Desk UX layer (Workspaces/Kanban/etc.) meant a human
  would actually be driving the browser: Frappe's Desk client always opens a
  socket.io connection on load and its client library retries indefinitely
  on failure, which is exactly what "infinite loop" describes. Fixed by
  adding an `erp-websocket` service (`node apps/frappe/socketio.js`, same
  as frappe_docker's own `pwd.yml`) to both compose files and pointing
  `erp-nginx`'s `SOCKETIO` env var at it. Verified live: `/socket.io/*`
  returns a real `200` handshake instead of `502`, and nginx logs show zero
  further `502`s after the fix. (Two other things flagged during the
  investigation turned out to be non-issues once checked directly: a
  smaller-than-expected repeated `/desk` response size was just gzip
  compression — a plain `curl` without `--compressed` doesn't reproduce it —
  and a single one-off `GET /desk/undefined` in the logs was not
  reproducible and not connected to any malformed Workspace fixture data,
  which was directly checked and is clean.) This turned out to be real but
  not the whole story — the user hit the loop again after this landed. The
  actual remaining cause: `bench new-site` leaves the `desktop:home_page`
  default at `"setup-wizard"` (`frappe/utils/install.py`), and it's only
  ever corrected to `"workspace"` by the *interactive* Setup Wizard's own
  completion step, which this app never runs (`after_install` sets
  `System Settings.setup_complete` directly instead). Every Desk boot
  therefore computed `home_page="setup-wizard"`, the client navigated
  there, the wizard saw setup was already done and bounced straight back to
  `/desk` — forever. Fixed in `hotel_erp.setup.install._finish_setup`
  (mirrors exactly what `setup_wizard.py`'s own `disable_future_access`
  does). Verified live: `home_page` now resolves to `"desktop"` and nginx
  logs show zero `setup_wizard.*` calls after the fix.
- **Real icons across every Workspace, sidebar item, and DocType** — two
  separate rendering gaps, both root-caused by reading Frappe's own
  icon-resolution code rather than guessing: 3 of the 7 top-level Workspace
  icons (`chart`, `card`, `home`) weren't valid names in the bundled lucide
  sprite and silently rendered nothing; and every left-sidebar menu entry
  showed a generic fallback icon regardless of what a Workspace's own
  shortcuts specified, because Frappe's own sidebar-generator
  (`create_workspace_sidebar_for_workspaces`) builds sidebar rows from
  `Workspace.shortcuts` but never copies `shortcut.icon` across — confirmed
  by reading that function directly, not assumed. Fixed with a small
  `hotel_erp.setup.workspace_icons` module that sets real icons on the
  generated sidebar rows directly (wired into `after_install` for fresh
  installs, plus a migrate-time patch for sites that installed before this
  fix existed) and corrected the 3 invalid top-level Workspace icons. Also
  added a real `icon` to all 28 DocTypes for breadcrumbs/global search.
  Verified live against both hotel-alpha and hotel-beta: header icons,
  sidebar item icons, and DocType icons all landed correctly after
  `bench migrate`.
- **Room Type photos/amenities: real upload widgets instead of hand-typed
  JSON** — `photos` and `amenities` were raw `JSON`-fieldtype textareas: a
  hotel operator wanting to add a photo had to host the file somewhere else
  themselves and paste the URL in by hand, and amenities needed literal
  `["wifi", "parking"]` array syntax typed correctly. Neither is realistic
  for actual hotel staff. Fixed by adding two child tables — `Room Type
  Photo` (an `Attach Image` field per row, so it's real drag-and-drop/browse
  upload, plus an optional caption; row order sets display order) and `Room
  Type Amenity` (one plain-text row per amenity) — and syncing them into the
  existing `photos`/`amenities` JSON fields from `RoomType.validate()`, which
  are now hidden/read-only on the form. This keeps the §4.4 API contract
  (`hotel_erp.api.serializers.serialize_room_type`) and every downstream
  consumer (Aggregator/Portal/Web) completely unaffected — verified directly
  against the serializer post-fix, output shape unchanged. Also added a
  `cover_image` field (auto-set to the first gallery photo) wired to the
  DocType's `image_field`, so the Room Type list/report view shows a real
  thumbnail instead of a blank row.

  Uploaded files must be public, since the Aggregator/Portal/Web render
  these URLs cross-origin with no Frappe session — a private (login-gated)
  file would silently 403 for everyone but the uploader. First cut flipped
  `is_private` with a raw `frappe.db.set_value`, which desyncs the flag from
  reality: Frappe physically relocates the file between `/private/files/`
  and `/files/` on disk, and only `File.save()` does that move — caught by a
  functional test (`is_private` read back as still `1` after the "fix" ran)
  before it shipped. Corrected to go through `File.save()` and re-read the
  resulting `file_url` (the move changes it) onto the gallery row. Verified
  live end-to-end against a real site: uploaded-file DB row correctly moved
  to `/files/...` with `is_private=0`, `photos` landed as a real absolute
  URL, `cover_image`/`amenities` populated correctly, and the public
  serializer's output shape confirmed unchanged for existing room types.

  Separately hit and worked around a Docker Compose footgun while deploying
  this: `erp-backend`/`erp-worker`/etc. mount a **named volume**
  (`erp_bench_apps`) at `apps/`, which — once created — persists across
  image rebuilds and silently shadows the image's own `apps/` directory.
  Rebuilding the image (even with `--no-cache`) was not enough for a code
  change to actually reach the running containers; the volume itself had to
  be deleted (safe — it only holds installed app code, reproducible from the
  image/git, not the database or site config) and repopulated fresh. Worth
  remembering for any future local iteration on this repo, not just this
  fix. Also hit BuildKit caching the `https://github.com/.../hotels_erp.git`
  git-context fetch across builds despite `--no-cache` (which only
  invalidates `RUN` layer cache, not the git source fetch) — needed
  `docker buildx prune -af` to force a truly fresh clone after a push.
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
