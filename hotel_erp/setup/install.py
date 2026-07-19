"""after_install setup for hotel_erp.

Creates the custom roles the DocType permission tables reference, and seeds the
Sync Config singleton with sane defaults so a freshly-installed site can boot
and answer GET /health without any manual configuration.
"""
from __future__ import annotations

import frappe

# Roles referenced by DocType permission tables. "Hotel API" is the identity the
# external /api/v1 methods run under; it is deliberately NEVER granted any
# permission on the Guest DocType (NFR-A9 / §5.6 guest-privacy boundary).
ROLES = ["Hotel API", "Revenue Manager", "Hotel Front Desk", "Housekeeping Staff"]


SERVICE_USER_EMAIL = "hotel-api@service.local"


def after_install() -> None:
    _create_roles()
    _create_service_user()
    _seed_sync_config()
    frappe.db.commit()


def _create_roles() -> None:
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 0 if role_name == "Hotel API" else 1,
                }
            ).insert(ignore_permissions=True)


def _create_service_user() -> None:
    """The identity `hotel_erp.api.auth.validate_bearer_token` authenticates
    the Aggregator's requests as. Deliberately never Administrator (NFR-A9)
    -- only the "Hotel API" role, which has no permission on Guest."""
    if frappe.db.exists("User", SERVICE_USER_EMAIL):
        return
    frappe.get_doc(
        {
            "doctype": "User",
            "email": SERVICE_USER_EMAIL,
            "first_name": "Hotel API",
            "user_type": "System User",
            "send_welcome_email": 0,
            "enabled": 1,
            "roles": [{"role": "Hotel API"}],
        }
    ).insert(ignore_permissions=True)


def _seed_sync_config() -> None:
    config = frappe.get_single("Sync Config")
    if not config.hold_ttl_seconds:
        config.hold_ttl_seconds = 300
    if not config.hotel_slug:
        # Dev default: derive a slug from the site name (e.g. "hotel-alpha" from
        # "hotel-alpha.localhost"). Override via the Sync Config form / onboarding.
        site = getattr(frappe.local, "site", "") or ""
        config.hotel_slug = site.split(".")[0] if site else "hotel"
    config.save(ignore_permissions=True)
