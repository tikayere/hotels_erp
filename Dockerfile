# hotel_erp -- Service A of the hotel booking ecosystem.
#
# Bakes the hotel_erp Frappe app straight into the frappe/erpnext base image,
# so no container needs to `bench get-app` at runtime. That matters for two
# reasons, both hit for real running this stack: (1) `bench get-app` isn't
# safely re-runnable against a volume where the app already exists -- it's
# been observed to clone a second, bogus copy that breaks Frappe's module
# resolution site-wide -- baking the app into the image sidesteps the whole
# class of problem instead of guarding around it; (2) erpnext ships modules
# ("Maintenance", "CRM") that collide by name with hotel_erp's own, breaking
# doctype sync for both -- stripped here, at build time, rather than by
# filtering sites/apps.txt at container startup (that filtering doesn't
# stick either: bench regenerates apps.txt from the apps/ directory's actual
# contents on its own, silently re-adding whatever's still physically
# present).
#
# This produces a complete, ready-to-serve image: `bench install-app
# hotel_erp` against a real site is still a per-site, per-container-startup
# step (it writes into that site's database), but nothing about *finding*
# hotel_erp's code is deferred to runtime anymore.
FROM frappe/erpnext:v16.28.0

USER root
RUN rm -rf /home/frappe/frappe-bench/apps/erpnext
USER frappe

WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:frappe . apps/hotel_erp

RUN /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir -e apps/hotel_erp && \
    ls -1 apps > sites/apps.txt

# Front Desk SPA (Vue 3 + frappe-ui, apps/hotel_erp/frontend). Built here so
# the image ships hotel_erp/public/frontend + hotel_erp/www/pms.html ready to
# serve -- no Node toolchain needed at container-start time, same reasoning
# as baking the Python app itself in above. frappe/erpnext base images carry
# Node + Yarn already (bench needs them to build the framework's own assets).
#
# NOTE the erp-apps-volume-gotcha this project has hit before: the compose
# stack mounts a *named volume* over apps/, which only ever seeds from this
# image on that volume's first-ever mount. Rebuilding this image alone does
# NOT update an already-running stack's frontend build -- `docker cp` the
# rebuilt hotel_erp/public/frontend and hotel_erp/www/pms.html into the
# running containers' volume (see frontend/README.md), same as any other
# hotel_erp source change.
RUN cd apps/hotel_erp/frontend && \
    yarn install --frozen-lockfile && \
    yarn build && \
    rm -rf node_modules

# `yarn build` alone produces hotel_erp/public/frontend, but nothing yet makes
# it reachable at /assets/hotel_erp/frontend/* -- that needs bench's own
# asset-linking step (creates the sites/assets/hotel_erp -> .../public
# symlink; also compiles any Desk-facing build.json bundles and translations,
# though this app has none). Confirmed live against a running site while
# building this: erp-nginx serves /assets/* straight off its own copy of this
# image (it doesn't mount the apps/ or sites/assets volumes at all -- see
# docker-compose.dev.yml), so that link has to be baked in at image-build
# time here, not deferred to a container-start step, or nginx never sees it.
RUN bench build --app hotel_erp
