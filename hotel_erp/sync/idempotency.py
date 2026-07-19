"""Idempotency-Key handling (contract section 4.10).

Wrap any whitelisted API method that must be idempotent -- POST
.../reservations/hold, .../confirm, .../release, and .../{id}/cancel --
with @idempotent(scope=...). scope distinguishes the four endpoints from
each other so the same physical key value can't collide across them.

Storage: an "Idempotency Record" DocType -- add it alongside the DocTypes
in doctype_spec.md section 4 (Data name, JSON response_body, Int
response_status, Data request_body_hash, Datetime expires_at), identical in
shape to the sibling bus project's. A daily scheduled job deletes rows past
expires_at (24h per the contract) -- see IMPLEMENTATION_GUIDE.md.
"""
from __future__ import annotations

import functools
import hashlib
import json
from datetime import timedelta
from typing import Callable

import frappe


class IdempotencyConflict(Exception):
    """Same Idempotency-Key, different request body (contract section 4.10).
    The caller should catch this and return 409 IDEMPOTENCY_KEY_CONFLICT
    per the error format in section 4.9.
    """


def idempotent(scope: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = _get_idempotency_key_header()
            body_hash = _hash_body(kwargs)
            record_name = _record_name(scope, key)

            existing = frappe.db.get_value(
                "Idempotency Record",
                record_name,
                ["request_body_hash", "response_body", "response_status"],
                as_dict=True,
            )
            if existing:
                if existing.request_body_hash != body_hash:
                    raise IdempotencyConflict("Idempotency-Key reused with a different request body")
                frappe.local.response["http_status_code"] = existing.response_status
                return json.loads(existing.response_body)

            result = fn(*args, **kwargs)
            status = frappe.local.response.get("http_status_code", 200)

            frappe.get_doc(
                {
                    "doctype": "Idempotency Record",
                    "name": record_name,
                    "request_body_hash": body_hash,
                    "response_body": json.dumps(result, default=str),
                    "response_status": status,
                    "expires_at": frappe.utils.now_datetime() + timedelta(hours=24),
                }
            ).insert(ignore_permissions=True)

            return result

        return wrapper

    return decorator


def _get_idempotency_key_header() -> str:
    key = frappe.request.headers.get("Idempotency-Key") if frappe.request else None
    if not key:
        frappe.throw("Idempotency-Key header is required", frappe.ValidationError)
    return key


def _hash_body(kwargs: dict) -> str:
    return hashlib.sha256(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()


def _record_name(scope: str, key: str) -> str:
    return hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()
