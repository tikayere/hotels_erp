"""Shared role constants and permission helpers for every session-authenticated
internal SPA API module (`hotel_erp.api.pms`, `.housekeeping`, `.maintenance`,
`.restaurant`, `.finance`, `.hr`, `.crm`, `.conference`, `.inventory`).

Split out of `pms.py` (which originally defined these for itself alone) once
a second module needed them -- every module below follows the same shape:
a per-domain "who may read" / "who may write" role tuple, matching that
domain's DocType permissions (see each doctype's `.json` `permissions`
block) as closely as the SPA's actual workflows allow, and a
`_require_role(roles)` call at the top of every whitelisted method rather
than relying on `frappe.get_doc(...).insert()`'s own permission check --
every method here calls `ignore_permissions=True` on writes (like
`pms.py` already does) so the *only* gate is this explicit role check, kept
close to the read/write role tuples so both can be reviewed together.
"""
from __future__ import annotations

import frappe

# Any logged-in hotel staff role may read shared/cross-module data (the
# dashboard's KPI counts, the Rooms board). Kept broad and low-stakes on
# purpose -- purely informational reads, no write ever uses this alone.
STAFF_ROLES = (
    "Hotel Front Desk",
    "Revenue Manager",
    "Housekeeping Staff",
    "Maintenance Staff",
    "Finance Manager",
    "HR Manager",
    "System Manager",
)
# Only front-desk-capable roles may write reservations/bookings -- same set
# `booking.direct_sale.create_walkin_reservation` already enforces.
DESK_ROLES = ("Hotel Front Desk", "Revenue Manager", "System Manager")

# Per-domain role tuples -- each mirrors that DocType's own `permissions`
# block (read+write+create granted to the same roles there), so the SPA
# never grants a role more than Desk itself would let it do directly.
HOUSEKEEPING_ROLES = ("Housekeeping Staff", "System Manager")
MAINTENANCE_ROLES = ("Housekeeping Staff", "Maintenance Staff", "System Manager")
RESTAURANT_ROLES = ("Hotel Front Desk", "System Manager")
FINANCE_ROLES = ("Finance Manager", "System Manager")
HR_ROLES = ("HR Manager", "System Manager")
CRM_ROLES = ("Hotel Front Desk", "System Manager")
CONFERENCE_ROLES = ("Hotel Front Desk", "System Manager")
# Inventory Item's own permissions grant Housekeeping Staff read-only and
# System Manager read/write; Purchase Order and Supplier grant System
# Manager alone. One read tier and one (narrower) write tier here mirrors
# that split rather than inventing a broader "Inventory Manager" role that
# doesn't exist yet.
INVENTORY_READ_ROLES = ("Housekeeping Staff", "System Manager")
INVENTORY_WRITE_ROLES = ("System Manager",)


def _require_role(roles: tuple[str, ...], message: str | None = None) -> None:
    if frappe.session.user in ("", "Guest"):
        frappe.throw("Authentication required", frappe.AuthenticationError)
    if not set(frappe.get_roles(frappe.session.user)) & set(roles):
        frappe.throw(message or f"Requires one of: {', '.join(roles)}", frappe.PermissionError)


def require_staff() -> None:
    _require_role(STAFF_ROLES)


def require_desk_role() -> None:
    _require_role(
        DESK_ROLES,
        "Only Hotel Front Desk, Revenue Manager or System Manager users may do this",
    )


def require_housekeeping_role() -> None:
    _require_role(HOUSEKEEPING_ROLES, "Only Housekeeping Staff may do this")


def require_maintenance_role() -> None:
    _require_role(MAINTENANCE_ROLES, "Only Housekeeping or Maintenance Staff may do this")


def require_restaurant_role() -> None:
    _require_role(RESTAURANT_ROLES, "Only Hotel Front Desk may do this")


def require_finance_role() -> None:
    _require_role(FINANCE_ROLES, "Only Finance Manager may do this")


def require_hr_role() -> None:
    _require_role(HR_ROLES, "Only HR Manager may do this")


def require_crm_role() -> None:
    _require_role(CRM_ROLES, "Only Hotel Front Desk may do this")


def require_conference_role() -> None:
    _require_role(CONFERENCE_ROLES, "Only Hotel Front Desk may do this")


def require_inventory_read() -> None:
    _require_role(INVENTORY_READ_ROLES, "Not permitted")


def require_inventory_write() -> None:
    _require_role(INVENTORY_WRITE_ROLES, "Only System Manager may do this")


def room_types_for_property(property_name: str | None) -> list[str] | None:
    """None means "no property filter"; a list (possibly empty) scopes to it."""
    if not property_name:
        return None
    return frappe.get_all("Room Type", filters={"property": property_name}, pluck="name") or [""]
