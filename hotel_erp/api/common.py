"""Shared helpers for the /api/v1 methods: ID (de)namespacing, entity
resolution, datetime formatting, bearer auth, and the @api_endpoint wrapper.
"""
from __future__ import annotations

import functools
from datetime import date, datetime
from typing import Callable

import frappe

from hotel_erp.api.errors import ApiError, respond_error
from hotel_erp.booking.atomic_hold import RoomsUnavailableError
from hotel_erp.sync.events import get_hotel_slug
from hotel_erp.sync.idempotency import IdempotencyConflict

# Framework-injected form_dict keys that must not leak into endpoint logic or the
# idempotency body hash.
_FRAMEWORK_KEYS = ("cmd",)


def strip_slug(global_id: str) -> str:
    """`"{hotel_slug}.{local_id}"` -> `local_id`. Tolerates an already-bare id."""
    if global_id is None:
        return global_id
    slug = get_hotel_slug()
    prefix = f"{slug}."
    if slug and global_id.startswith(prefix):
        return global_id[len(prefix):]
    # Fall back to splitting on the first dot if the prefix doesn't match the
    # configured slug (defensive; keeps behaviour sane in mis-onboarded dev).
    return global_id.split(".", 1)[1] if "." in global_id else global_id


def resolve_room_type(room_type_id: str):
    """Resolve an exposed room_type_id ("{slug}.{code}") to its Room Type doc.
    The exposed local part is the per-property `code`, not the hash docname
    (contract §4.4 uses the code; §3.4 stores "{hotel_slug}.{room_type_code}")."""
    code = strip_slug(room_type_id)
    name = frappe.db.get_value("Room Type", {"code": code}, "name")
    if not name:
        raise ApiError("NOT_FOUND", f"Unknown room type '{room_type_id}'", 404)
    return frappe.get_doc("Room Type", name)


def resolve_rate_plan(room_type_name: str, rate_plan_code: str):
    name = frappe.db.get_value(
        "Rate Plan", {"room_type": room_type_name, "code": rate_plan_code}, "name"
    )
    if not name:
        raise ApiError(
            "NOT_FOUND", f"Unknown rate plan '{rate_plan_code}' for the room type", 404
        )
    return frappe.get_doc("Rate Plan", name)


def iso_utc(value) -> str:
    """Format a stored UTC Datetime as ISO-8601 with a trailing Z. The site is
    pinned to UTC (doctype_spec.md §1.2) so no conversion is needed."""
    if value is None:
        return None
    dt = frappe.utils.get_datetime(value) if not isinstance(value, datetime) else value
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return frappe.utils.getdate(value)


def parse_int(value, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _check_bearer() -> None:
    """Bearer auth (contract §4.2). Compares the presented token to Sync Config's
    aggregator_api_key. If no key is configured (fresh dev site), auth is left
    open so the stack boots without manual onboarding — configure the key to
    enforce it."""
    configured = frappe.utils.password.get_decrypted_password(
        "Sync Config", "Sync Config", "aggregator_api_key", raise_exception=False
    ) if frappe.db.exists("Sync Config", "Sync Config") else None
    if not configured:
        return  # dev / not-yet-onboarded: do not enforce
    header = frappe.get_request_header("Authorization") or ""
    token = header[len("Bearer "):].strip() if header.startswith("Bearer ") else ""
    if token != configured:
        raise ApiError("UNAUTHORIZED", "Missing or invalid credentials", 401)


def api_endpoint(require_auth: bool = True) -> Callable:
    """Wraps a whitelisted /api/v1 method: strips framework keys, enforces bearer
    auth, and funnels every exception into the §4.9 error envelope with the right
    status code."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for k in _FRAMEWORK_KEYS:
                kwargs.pop(k, None)
            try:
                if require_auth:
                    _check_bearer()
                return fn(*args, **kwargs)
            except ApiError as e:
                return respond_error(e.code, e.message, e.http_status, e.details)
            except IdempotencyConflict:
                return respond_error(
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "Idempotency-Key reused with a different request body",
                    409,
                )
            except RoomsUnavailableError as e:
                return respond_error(
                    "ROOMS_UNAVAILABLE",
                    "Requested room count is not available for one or more nights in the stay.",
                    409,
                    {"unavailable_dates": e.unavailable_dates},
                )
            except frappe.DoesNotExistError:
                return respond_error("NOT_FOUND", "Unknown resource", 404)
            except (frappe.ValidationError, ValueError) as e:
                return respond_error("VALIDATION_ERROR", str(e) or "Malformed request", 400)
            except Exception:
                frappe.log_error(title="hotel_erp API error", message=frappe.get_traceback())
                return respond_error("INTERNAL_ERROR", "Internal server error", 500)

        return wrapper

    return decorator
