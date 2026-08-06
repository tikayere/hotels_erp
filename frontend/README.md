# Hotel Staff SPA

A Vue 3 + [frappe-ui](https://github.com/frappe/frappe-ui) single-page app for
hotel staff, served by Frappe at **`/pms`**. Scaffolded the standard Frappe
way — `frappeui/vite` plugin, `vue-router`, Frappe session auth — see
[ui.frappe.io](https://ui.frappe.io) for the framework itself.

## What's covered today

Front Desk/Reservations plus every other internal module
(housekeeping, maintenance, restaurant, finance, HR, CRM, conference,
inventory) — see "Roadmap" below for what's still Desk-only (revenue/rate
management, plus anything not listed in the table below).

| Module | Page | Route | What it does |
|---|---|---|---|
| Front Desk | Dashboard | `/pms` | Today's arrivals/departures/in-house counts, room-status breakdown, open housekeeping/maintenance counts. |
| Front Desk | Rooms | `/pms/rooms` | Room board — status per room, current guest + check-out date for occupied rooms. |
| Front Desk | Reservations | `/pms/reservations` | Searchable/filterable reservation list. |
| Front Desk | Reservation detail | `/pms/reservations/:id` | Full detail + **Check In** (room picker), **Check Out**, **Cancel**. |
| Front Desk | New Reservation | `/pms/reservations/new` | Walk-in booking: room type → rate plan → dates → live availability/price preview → guests. |
| Housekeeping | Board | `/pms/housekeeping` | Task board (filter by status/mine), **+ New Task**. |
| Housekeeping | Task detail | `/pms/housekeeping/:id` | **Assign**, **Start**, **Complete**, **Verify** — the last two flip the room `dirty → clean → available`. |
| Maintenance | Board | `/pms/maintenance` | Request list (filter by status/priority), **+ New Request** (auto-flags the room `maintenance`/`out_of_order` if it isn't occupied). |
| Maintenance | Request detail | `/pms/maintenance/:id` | **Assign** technician, **Start**, **Resolve** (routes the room back through `dirty`, not straight to `available`), **Close**. |
| Restaurant | Orders | `/pms/restaurant` | Order list, **+ New Order**. |
| Restaurant | New Order | `/pms/restaurant/new` | Line-item entry with live total. |
| Restaurant | Order detail | `/pms/restaurant/:id` | Advance `placed → in_kitchen → served → billed`, or **Cancel**. |
| Finance | Transactions | `/pms/finance` | KPI totals by type, transaction list, **+ New Transaction** (draft), **Submit**/**Cancel**. |
| HR | Staff | `/pms/hr/staff` | Directory, **+ Add Staff**, edit department/status/rate. |
| HR | Leave | `/pms/hr/leave` | Applications list, **+ New Application**, **Approve**/**Reject**. |
| HR | Payroll | `/pms/hr/payroll` | **Run Payroll** for a period, **Process**/**Mark Paid** each entry. |
| CRM | Guests | `/pms/guests` | Searchable guest directory. |
| CRM | Guest detail | `/pms/guests/:id` | Profile + communication log (**+ Log**) + complaints (**+ New**). |
| CRM | Complaints | `/pms/complaints` | Cross-guest complaint queue, **Resolve**/**Escalate**. |
| Conference | Bookings | `/pms/conference` | Space booking list, **Confirm**/**Cancel**, overlap-checked **+ New Booking**. |
| Inventory | Items | `/pms/inventory` | Stock levels, low-stock filter, **+ New Item** (System Manager only to write — see below). |
| Inventory | Suppliers | `/pms/inventory/suppliers` | Directory, **+ New Supplier**. |
| Inventory | Purchase Orders | `/pms/inventory/purchase-orders` | **+ New PO**, **Mark Ordered**, **Mark Received** (increments each line's stock). |

Every module talks to its own `hotel_erp/api/<module>.py` — all
**session-authenticated** internal APIs (Desk login, staff roles), distinct
from `hotel_erp/api/v1.py` (the bearer-token Aggregator contract at
`/api/v1/*`). Shared role tuples and `require_*_role()` gates live in
`hotel_erp/api/pms_common.py`; `pms.py`'s `get_boot_info` exposes which
modules the current user may see (`_MODULE_ROLES`) so `AppShell.vue`'s nav
can gate itself the same way server-side permissions do. `pms.py` (Front
Desk/Reservations specifically) also reuses the booking/inventory primitives
(`booking.atomic_hold`, `booking.direct_sale`) so a booking or cancellation
made here never lets the Aggregator's cache drift (FR-A18) — see that file's
module docstring.

**Read/write role split, by module** (see `pms_common.py` for the exact
tuples): Housekeeping/Maintenance/Restaurant/Conference are staff-broad on
read (any logged-in role sees the board) but role-narrow on write, since a
room's operational status is everyone's business but only the responsible
role should change it. Finance/HR are role-narrow on **both** — payroll and
transaction amounts aren't broad-staff-readable. CRM is role-narrow on both
too (guest contact history isn't broadly readable either). Inventory reads
are Housekeeping Staff + System Manager (mirroring `Inventory Item`'s own
DocType permissions); every inventory write is System-Manager-only
(mirroring `Purchase Order`/`Supplier`, which grant no other role anything —
there's no dedicated purchasing role in this codebase yet). The Inventory
pages hide their own create/edit affordances client-side for a
Housekeeping-Staff viewer (`canWrite` in each page) since the server would
403 anyway — the server-side gate is what's actually enforced, this is UX
polish, not the security boundary.

## Roadmap: alongside Desk, not a replacement yet

`hooks.py`'s `role_home_page` sends every staff role except System Manager
here on login now that each one has at least one module in the SPA; Desk
(`/app`) is still how anything not in the table above gets worked (revenue
management/rate plans/pricing rules being the main gap — still Desk-only).
The intent is for this SPA to keep growing until Desk isn't needed
day-to-day at all; each new module should get its own page(s) +
`hotel_erp/api/<module>.py` endpoints following the pattern above, not a
parallel API style.

## Local development

```bash
cd erp/frontend
yarn install
yarn dev            # Vite dev server on :8080, HMR, proxies /api etc. to the Frappe backend on :8000
```

The dev server needs a running Frappe backend to proxy to (`bench start`, or
point at the dev compose stack's `erp-backend`). CSRF checks reject the
Vite dev server's cross-origin requests by default — disable per-site while
developing:

```bash
bench --site hotel-alpha.localhost set-config ignore_csrf 1
```

(Never set that in a deployed environment — it's a dev-only escape hatch.)

## Production build

```bash
cd erp/frontend
yarn build
```

Outputs to `../hotel_erp/public/frontend` (assets) and copies `index.html`
to `../hotel_erp/www/pms.html` (see `vite.config.js`'s explicit
`buildConfig` — the plugin's own path auto-inference needs a real bench's
`sites/common_site_config.json` a few directories up, which isn't always
there depending on how this repo is checked out/built). Both output paths
are gitignored — regenerated by this command (or by `erp/Dockerfile`, which
runs it at image-build time), never hand-edited or committed.

Equivalent via bench, once the app is installed on a bench: `bench build
--app hotel_erp`.

## Deploying a change to the running dev stack

`erp/Dockerfile` builds this SPA into the `hotels-erp:dev` image, but **the
dev compose stack's named `erp_bench_apps` volume shadows that image's
`apps/` directory after its first-ever mount** (see the
`erp-apps-volume-gotcha` note — same failure mode as any other
`hotel_erp/**` source change, not specific to the frontend). Rebuilding the
image alone will not update an already-running stack. To push a rebuilt
frontend into it:

```bash
# 1. Rebuild locally (or let the image build do it)
cd erp/frontend && yarn build

# 2. Copy the build output into a container that mounts the shared volume
docker cp erp/hotel_erp/public/frontend hotels-erp-backend-1:/home/frappe/frappe-bench/apps/hotel_erp/public/frontend
docker cp erp/hotel_erp/www/pms.html    hotels-erp-backend-1:/home/frappe/frappe-bench/apps/hotel_erp/www/pms.html
docker cp erp/hotel_erp/www/pms.py      hotels-erp-backend-1:/home/frappe/frappe-bench/apps/hotel_erp/www/pms.py

# 3. Link the new build into /assets/hotel_erp/* on the backend container
#    (confirmed necessary live — a bare `yarn build` alone isn't enough):
docker exec hotels-erp-backend-1 bench build --app hotel_erp
docker exec hotels-erp-backend-1 bench --site hotel-alpha.localhost clear-cache
docker exec hotels-erp-backend-1 bench --site hotel-beta.localhost clear-cache

# 4. Restart so any changed Python (www/pms.py, api/pms.py) reloads —
#    --preload gunicorn workers only import once at start.
docker restart hotels-erp-backend-1 hotels-erp-worker-1 hotels-erp-scheduler-1 hotels-erp-websocket-1

# 5. erp-nginx has its own on-disk `assets/hotel_erp` (not a volume shared
#    with the backend — confirmed on two separate occasions now, see the
#    Architecture notes below), so step 3's `bench build` there is INVISIBLE
#    to it. Refresh nginx's copy directly (`assets/hotel_erp/frontend`, not
#    `sites/assets/...` — the latter is itself a symlink to the former, see
#    below):
docker exec hotels-erp-nginx-1 rm -rf /home/frappe/frappe-bench/assets/hotel_erp/frontend
docker cp erp/hotel_erp/public/frontend/. hotels-erp-nginx-1:/home/frappe/frappe-bench/assets/hotel_erp/frontend
```

If `hooks.py` changed too (new `website_route_rules` / `role_home_page`
entries), also run `bench --site <site> migrate` before the restart, same as
any other hooks.py change.

The most reliable way to get a fully consistent state on every service
including `erp-nginx` is still `docker compose up -d --build` (recreating
every container from the freshly-built image) — the volume-shadowing and
nginx-assets-drift issues above only bite an *already-running* stack; the
`docker cp` sequence is for iterating on one without a full rebuild/recreate
cycle. Confirm step 5 actually took by diffing a hashed filename between
containers, not just "no errors":
```bash
docker exec hotels-erp-backend-1 sh -c "ls assets/hotel_erp/frontend/assets | grep '^index-'"
docker exec hotels-erp-nginx-1    sh -c "ls assets/hotel_erp/frontend/assets | grep '^index-'"
# both must print the same hash
```

## Architecture notes for anyone extending this

- **Auth**: session cookie only. `www/pms.py`'s `get_context` calls
  `frappe.redirect(...)` for a Guest — confirmed live that
  `frappe.throw(..., frappe.PermissionError)` does NOT redirect here, it
  renders a 403 "Not Permitted" page with a Login button instead (see
  `frappe.website.page_renderers.not_permitted_page`); `frappe.redirect`
  (raises `frappe.exceptions.Redirect`) is the real mechanism, the same one
  core's own `www/desk.py` (`/desk`) uses for this exact case. The SPA itself
  never renders a login form — a Guest is bounced to
  `/login?redirect-to=/pms/...` before the Vue app ever mounts.
  `src/router.js`'s navigation guard re-checks on every client-side route
  change too (a session can expire mid-visit).
- **Data fetching**: `frappe-ui`'s `createResource` throughout (see
  `src/api/pms.js`) — no extra HTTP client, no Pinia (one shared piece of
  state, `src/session.js`, is a plain reactive singleton; add a real store if
  a second one shows up).
- **IDs**: every `hotel_erp.api.*` internal-SPA method takes/returns **bare**
  Frappe docnames, never the Aggregator contract's `"{hotel_slug}."`-namespaced
  form — see `pms.py`'s module docstring. Don't reuse `hotel_erp.api.v1.*`
  methods directly from this app for that reason (`create_walkin_reservation`
  is the one exception, and it re-shapes the response — read that function's
  docstring before adding a second one like it).
- **Permissions**: `hotel_erp/api/pms_common.py` holds one role tuple +
  `require_<x>_role()` gate per module (Housekeeping, Maintenance,
  Restaurant, Finance, HR, CRM, Conference, Inventory), each mirroring that
  module's own DocType `permissions` block rather than inventing new
  access rules — check there before writing a new endpoint, most modules
  already have the gate you need. `pms.get_boot_info`'s `modules` list (one
  dict, `_MODULE_ROLES`, mapping module key -> role tuple) is what
  `AppShell.vue`'s nav filters against, so a role added to a module there
  shows up in the sidebar automatically — no second place to edit.
- **New page checklist**: add the route in `src/router.js`; add the API
  method(s) to the right `hotel_erp/api/<module>.py` (or a new one, wired
  into a new `require_<module>_role()` in `pms_common.py` for a genuinely
  new module) rather than piling onto `pms.py`, which stays
  Front-Desk/Reservations-only by convention; add a thin `createResource`
  factory in the matching `src/api/<module>.js`; add the nav entry (and, for
  a new module, a `module:` key + section) in `src/components/AppShell.vue`.
- **nginx's `/assets/hotel_erp` is not the same filesystem as the
  backend's**, confirmed on two separate occasions building this out (see
  "Deploying a change" above): `sites/assets` is itself a bench-standard
  symlink to `../assets` (one level up, outside the shared `sites` volume),
  so even though `hotels-erp-nginx-1` and `hotels-erp-backend-1` mount the
  *same* `sites` volume, that symlink resolves to each container's own,
  separate on-disk `frappe-bench/assets/` — real content on the backend
  (which also mounts `apps/`, so `bench build` there links live into the
  mounted source), but whatever was baked into nginx's own image layer on
  the other. A fresh `docker compose up -d --build` bakes matching content
  into both; an already-running nginx container needs its copy refreshed by
  hand (step 5 above) after every `hotel_erp` frontend change.
