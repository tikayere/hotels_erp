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

  A real user then hit a live crash this testing hadn't caught: saving an
  *existing* Room Type after uploading a fresh photo 500'd with
  `MySQLdb.OperationalError: (1054, "Unknown column 'image' in 'SET'")`.
  Root cause is a genuine Frappe quirk, not something specific to this app:
  Desk's uploader records a file uploaded into a child table's `Attach
  Image` field against the *parent* document (`attached_to_doctype="Room
  Type"`, `attached_to_name=`the Room Type being edited) rather than the
  child row, but leaves `attached_to_field` as the *child's* own fieldname
  (`"image"`) — which isn't a real column on the parent at all. Flipping
  `is_private` through `File.save()` (see above) triggers Frappe's own
  is_private-changed handling, which then does an unconditional `UPDATE
  <attached_to_doctype> SET <attached_to_field> = ...` write-back and 1054s
  on that mismatch. Reproduced directly against the exact shape of the live
  crash (an already-saved parent) before fixing, and in the process found a
  *second* failure mode of the same quirk: if `attached_to_field` is unset,
  Frappe falls back to loading the parent by name to guess the field, which
  throws `DoesNotExistError` instead for a brand-new, not-yet-saved parent.
  Fixed with `_attached_to_is_resolvable()`, which checks the parent
  document actually exists and the field is real before trusting
  `attached_to_*` at all, clearing all three otherwise — harmless, since
  `row.image` is already set from the File's resulting `file_url` right
  after regardless. Verified against both real scenarios (a fresh unsaved
  parent, and editing an existing already-saved Room Type matching the live
  crash exactly) before redeploying.

  A second live crash surfaced right after, on the same Room Type:
  `FileExistsError: A file with same name .../public/files/kari-shea-....jpg
  already exists`. Different root cause: Frappe's own upload-time filename
  dedup (`frappe.core.doctype.file.utils`) only checks for a collision
  within the file's *current* privacy folder, so it can't catch a fresh
  private upload that collides with a file of the same name already public
  elsewhere — that only surfaces later, at the move. Confirmed directly
  against the live DB: two separate `File` rows both named
  `kari-shea-....jpg`, one already public from an earlier save, one freshly
  uploaded and still private, identical `content_hash` — genuinely the same
  photo re-uploaded (a plausible retry after the first crash above, but not
  specific to it — re-uploading any previously-added photo hits this the
  same way). Fixed with `_avoid_public_name_collision()`, following the same
  convention Frappe's own `File.validate_duplicate_entry` already uses
  elsewhere (compare by `content_hash`, not filename): same content as the
  existing public file → reuse its URL instead of creating a duplicate;
  different content that only coincidentally shares a name (e.g. two
  unrelated phone photos both named `IMG_0001.jpg`) → rename to a free name
  first (a private-folder-only move, safe to do directly) so the later move
  doesn't collide. First test of the second path was itself flawed —
  accidentally reused identical photo bytes across both branches, so
  Frappe's own dedup silently merged them before the new code ever ran and
  the rename branch went untested — caught by asserting the two branches'
  `content_hash`es actually differ, fixed, and reverified for real before
  shipping.

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
- **Room Type photo URLs unreachable outside the container, found and
  fixed** — reported as "room type images don't load on the web/portal, not
  a Frappe problem." Two independent bugs stacked on the same document:

  1. `_sync_photos_from_gallery()`'s `get_url(row.image)` call (see above)
     resolves against `frappe.utils.get_url()`, which — with no `host_name`
     configured and no HTTP request context (any background job, script, or
     webhook-triggered save) — falls back to a bare `http://<site>` with
     **no port**. `erp-nginx` publishes both sites on host port 8001, not
     80, so every photo URL synced this way pointed at a port nothing is
     listening on; confirmed directly (`get_url()` returns
     `http://hotel-alpha.localhost/files/...` outside a request, vs.
     `...localhost:8001/files/...` once `host_name` is set — `get_url()`
     checks `conf.host_name` before anything else, so setting it makes the
     URL correct and deterministic in every context, not just real desk-UI
     saves). Fixed by setting `host_name` on both sites (now baked into
     `erp-install-app`'s bootstrap command in both compose files) and
     re-saving the affected Room Type to regenerate its `photos` field.
  2. That re-save initially had no effect — traced to the *existing* Room
     Type carrying `docstatus=1` despite the doctype not being submittable
     (`is_submittable=0`), almost certainly a leftover artifact from an
     earlier debugging session's test script. Frappe's `_save()` maps that
     docstatus transition to `_action = "update_after_submit"`, which
     **skips calling `validate()` entirely** — so none of this controller's
     logic (photo/amenity sync, the per-property unique-code check) has run
     on any save of that document since. Fixed by resetting `docstatus` to
     `0` directly, confirmed a subsequent real `.save()` now invokes
     `validate()` and regenerates `photos` correctly.

  Chasing why the corrected URL still wasn't reaching the Aggregator
  surfaced a third, larger gap: **Sync Config's `aggregator_base_url` /
  `aggregator_webhook_secret` had never been set for either site**, so
  `dispatch_pending_webhooks` (`hotel_erp/sync/dispatcher.py`) was
  returning immediately on every scheduled run — confirmed live: 388
  Webhook Outbox rows going back to this environment's creation, 100% still
  `status=pending`, meaning *no* ERP-side change (not just this one) had
  ever reached the Aggregator via webhook. Fixed by setting
  `aggregator_base_url` to the internal service DNS name
  (`http://aggregator:8000`, now also baked into both compose files'
  bootstrap) and provisioning a fresh `aggregator_webhook_secret` matching
  what's registered for `hotel-alpha` on the Aggregator side (via its
  `PATCH /admin/hotels/{slug}` operator endpoint) — the secret itself is
  deliberately *not* in compose, since it must match a credential issued at
  hotel-onboarding time, not a fixed default. Manually drained the 388-row
  backlog afterward; new changes now dispatch within the cron's normal
  1-minute cadence. `hotel-beta` has no Room Types yet and isn't onboarded
  on the Aggregator side at all, so it only got the `host_name` /
  `aggregator_base_url` half of this fix for parity — nothing to drain.

- **Internal module workflow logic** (FR-A8–A15, a scoped subset — the
  contract's own note allows "internal-only, build per usual Frappe
  conventions," lowest priority of anything tracked in this repo's gap
  list): five real workflows, none crossing the §4.5 API boundary
  themselves (only the webhooks they trigger, where applicable, do).
    - **Housekeeping auto-assignment** — a Reservation transitioning to
      `checked_out` (`reservation/events.py`) flips its Room to `dirty` and
      creates a `Housekeeping Task` (type `cleaning`), auto-assigned to the
      least-loaded active Housekeeping-department Staff member with a
      linked User.
    - **Kitchen order routing** — a `Restaurant Order` transitioning to
      `in_kitchen` is auto-assigned the same way, among active
      Restaurant-department Staff.
    - **Stock consumption** — a `Restaurant Order` transitioning to
      `served` decrements `Inventory Item.quantity_on_hand` for every line
      whose `item` name exactly matches a tracked Inventory Item (floored
      at 0, never negative). Deliberately scoped: there's no recipe/BOM
      doctype mapping menu items to ingredients, so only line items that
      themselves name a tracked item (e.g. a bottled drink) are decremented
      — real recipe-based consumption is a genuine feature, not "internal
      workflow" scope.
    - **Payroll calculation** — `hotel_erp.hr.payroll.generate_payroll_entries`
      creates one draft `Payroll Entry` per active Staff member with a
      `daily_rate_minor` set, `gross = daily_rate_minor × days_in_period`
      (flat day-rate; there's no Attendance/timesheet doctype to derive
      hours from), a flat 10% deduction placeholder, idempotent per
      (staff, period). `Payroll Entry.net_amount_minor` is now always
      derived in `validate()`, for hand-created entries too.
    - **Night audit** — a new daily scheduled job
      (`hotel_erp.reservation.night_audit.run_night_audit`) flags
      `confirmed` reservations whose `check_in` has passed without a
      check-in as `no_show`, going through the normal `doc.save()` path so
      the existing `reservation.no_show` webhook (§4.7) fires exactly as it
      would for a manually-marked no-show. No inventory is released — a
      no-show is a revenue event, not a cancellation (matches
      `atomic_hold.py`'s own "stays decremented through confirm" rule).

  The auto-assignment helper (`hotel_erp/hr/staff_assignment.py`) picks the
  active Staff member in a department with the fewest currently-open
  records, but only among Staff with a linked `User` — `assigned_to` on
  both Housekeeping Task and Restaurant Order is a Link to `User`, not
  `Staff`, and an early version of this that fell back to the `Staff`
  docname when no User was linked produced an invalid link and threw on
  save; caught by live verification, not by inspection.

  **Verified live** (2026-07-28) against the running dev containers, all
  five in one pass: created a checked-in reservation and transitioned it to
  `checked_out` (task created, room flipped to `dirty`, assigned to the
  test Housekeeping user); created a Restaurant Order and drove it through
  `placed → in_kitchen → served` (auto-assigned to the test kitchen user;
  a tracked line item's stock went 10 → 7, an untracked freeform line was
  correctly left alone); called `generate_payroll_entries` for a 7-day
  period against a 15000-minor-unit/day test rate (gross 105000,
  deductions 10500, net 94500 — all exactly as computed); created an
  overdue-check-in
  reservation and ran `run_night_audit()` (flipped to `no_show`). All test
  fixtures removed afterward — confirmed no residue left in the shared dev
  database. Along the way, discovered and worked around a real deployment
  gotcha specific to this repo: the dev stack's `erp_bench_apps` Docker
  volume shadows the image's baked-in app code once created, so rebuilding
  `hotels-erp:dev` alone does **not** deploy source changes to an
  already-running stack — needs a direct `docker cp` into the volume plus
  `bench migrate` plus a container restart (see this session's memory notes
  for the full mechanism; not specific to this feature, but this is where
  it was first hit).

- **NFR-A7 automated backups** — `hotel_erp/ops/backup.py`'s
  `run_daily_backup`, registered per-site in `scheduler_events["daily_long"]`
  (a longer slot than plain `"daily"`, matching that a DB+files dump can
  run past a quick job's expected duration). Calls the same
  `frappe.utils.backups.new_backup` a manual `bench backup` does (DB dump +
  public/private files, `force=True` so the daily cadence isn't skipped by
  `new_backup`'s own "skip if last backup < 6h old" throttle), then prunes
  backup sets older than `backup_retention_days` in that site's
  `site_config.json` (default 7) — matching on the whole
  `YYYYMMDD_HHMMSS-` timestamp prefix every file in one backup set shares,
  so a purge is always atomic per set, never half-deleting one. Retention
  window is deliberately per-site config, not a hotel_erp-wide setting —
  backup storage policy is an infra decision for whoever deploys a given
  site. **Verified live** (2026-07-28): ran it for real against
  `hotel-alpha.localhost` and confirmed 4 genuine, non-trivial backup files
  landed in `private/backups/` (database.sql.gz ~330KB, files.tar ~174KB,
  private-files.tar ~133KB, site_config_backup.json); separately planted a
  fake 10-day-old backup set and a fake same-day one, ran the purge, and
  confirmed only the stale set was removed — the fresh fake file and the
  real backup just taken were both left alone.

## Implemented, but thinner than the spec describes

- **FR-A8–A15 internal modules** (Housekeeping, Maintenance, Restaurant,
  Conference, Finance, HR, Inventory, CRM) — DocTypes exist with the fields
  the contract's logical schema (§2.4) calls for. Five of these now have
  real workflow logic, not just plain CRUD (see "Fully implemented" above
  for the full writeup); the rest — Maintenance repair-request routing,
  Conference booking/catering, Finance invoicing, CRM complaint routing —
  are still plain CRUD. Matches the spec's own framing of this whole group
  as "internal-only, build per your usual Frappe conventions," but worth
  tracking since "a DocType exists" and "the workflow works" aren't the same
  claim.
- **FR-A16 analytics** — the occupancy/ADR/RevPAR/reception reports above
  are Query Reports, not full dashboards.

- **`hotel-beta` onboarded for real** — was a completely empty site (zero
  Property/Room Type/Rate Plan/Rate Calendar rows), so it existed in the
  compose topology but wasn't a real second hotel in the marketplace.
  `hotel_erp/patches/onboard_beta_demo_data.py` (run via `bench --site
  hotel-beta.localhost execute hotel_erp.patches.onboard_beta_demo_data.execute`,
  idempotent) seeds a Property ("Coral Beach Resort", Zanzibar City),
  one Room Type, one Rate Plan, and 60 days of Rate Calendar rows. Sync
  Config's `aggregator_base_url`/`aggregator_webhook_secret`/`aggregator_api_key`
  are now set (previously unset — the same silent-no-op gap `hotel-alpha` had
  before it was fixed, see above), and a matching `Hotel`/`HotelCredential`
  now exists on the Aggregator side. Verified live end-to-end: the seeded
  Room Type's `room_type.created` webhook was delivered and marked `sent`
  in Webhook Outbox, a manual reconciliation pull populated
  `rate_availability_index`, and `GET /api/v1/search` (no filters) now
  returns both `hotel-alpha` and `hotel-beta`.

- **First automated test suite** — `tests/`: a live-HTTP integration suite
  (deliberately not `bench run-tests`/FrappeTestCase — the two things worth
  proving here, NFR-A2 concurrency under real MariaDB lock contention and
  the bearer-auth service-user permission boundary, only mean something
  over a real HTTP+DB round trip). Covers **NFR-A2** (`ThreadPoolExecutor`-driven
  genuinely concurrent holds against the same room-type/dates never oversell,
  and disjoint-date holds never wrongly serialize against each other — both
  run against a real running site, not mocked), **§4.10 idempotency**
  (replay-same-body vs. replay-different-body), **NFR-A9/§5.6 guest privacy**
  (the `hotel-api@service.local` bearer-auth user can't read the `Guest`
  DocType at all, and a confirmed reservation's response never carries
  `passport_no`/`national_id`), and a pure round-trip test of
  `webhook_signing.py`. `docker-compose.ci.yml` bootstraps a fresh
  single-site instance of this exact image from scratch (new-site,
  install-app, migrate, seed via `onboard_beta_demo_data.py`, known test
  bearer token) so CI tests exactly what ships — wired into
  `.github/workflows/docker-publish.yml` as a required `test` job the image
  build now depends on. Verified twice locally end-to-end against the real
  CI recipe (`docker compose -f docker-compose.ci.yml up -d --build`,
  poll-until-ready, run `pytest tests/`) — the first attempt surfaced a real
  test-authoring mistake (a stray `docker cp` nested `tests/` inside itself,
  doubling concurrent requests and producing a false "oversold" read from
  leftover unreleased holds, not a real bug), the second, from a genuinely
  fresh site, passed clean: 12/12.

## Not implemented

- Everything in the contract's own **§6 "Open Items for Future Phases"**:
  channel-manager/OTA integration, Event Marketplace, digital
  check-in/smart-lock/IoT, cross-hotel loyalty, corporate booking with
  negotiated rates, multi-currency/multi-country tax handling. These were
  explicitly deferred at the design stage, not accidentally dropped.
