"""Contract §4.9 error format + HTTP status mapping.

Every /api/v1 method funnels its failures through ApiError -> the §4.9 envelope:

    {"error": {"code", "message", "trace_id", "details"?}}

with the status codes from the §4.9 table.
"""
from __future__ import annotations

import uuid

import frappe


class ApiError(Exception):
    def __init__(self, code: str, message: str, http_status: int, details: dict | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details
        super().__init__(message)


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    err = {"code": code, "message": message, "trace_id": str(uuid.uuid4())}
    if details is not None:
        err["details"] = details
    return {"error": err}


def respond_error(code: str, message: str, http_status: int, details: dict | None = None) -> dict:
    frappe.local.response["http_status_code"] = http_status
    return error_body(code, message, details)
