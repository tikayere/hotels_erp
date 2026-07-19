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
