"""Clean /api/v1/* REST routing on top of Frappe's method dispatch.

See the routing comment in hooks.py. `route_v1` (before_request) maps the REST
path to a hotel_erp.api.v1 method via form_dict.cmd; `unwrap_v1` (after_request)
strips Frappe's {"message": ...} envelope so the body matches the OpenAPI schema.

A guaranteed fallback also exists without this shim: every endpoint is a plain
@frappe.whitelist() method callable at /api/method/hotel_erp.api.v1.<fn>.
"""
from __future__ import annotations

import json

import frappe

_PREFIX = "/api/v1/"


def _match(segments: list[str], method: str):
    """Return (fn_name, path_params) for a matched route, else None."""
    n = len(segments)
    if n == 1 and segments[0] == "health" and method == "GET":
        return "get_health", {}
    if n == 1 and segments[0] == "room-types" and method == "GET":
        return "list_room_types", {}
    if n == 2 and segments[0] == "room-types" and method == "GET":
        return "get_room_type", {"room_type_id": segments[1]}
    if n == 1 and segments[0] == "availability" and method == "GET":
        return "get_availability", {}
    if n == 2 and segments[0] == "reservations" and segments[1] == "hold" and method == "POST":
        return "create_hold", {}
    if n == 3 and segments[0] == "reservations" and segments[2] == "confirm" and method == "POST":
        return "confirm_hold", {"hold_id": segments[1]}
    if n == 3 and segments[0] == "reservations" and segments[2] == "release" and method == "POST":
        return "release_hold", {"hold_id": segments[1]}
    if n == 3 and segments[0] == "reservations" and segments[2] == "cancel" and method == "POST":
        return "cancel_reservation", {"reservation_id": segments[1]}
    if n == 2 and segments[0] == "reservations" and method == "GET":
        return "get_reservation", {"reservation_id": segments[1]}
    return None


def route_v1():
    request = getattr(frappe.local, "request", None)
    if request is None:
        return
    path = request.path or ""
    if not path.startswith(_PREFIX):
        return
    sub = path[len(_PREFIX):].strip("/")
    if not sub:
        return
    segments = sub.split("/")
    matched = _match(segments, request.method)
    if not matched:
        return
    fn_name, params = matched

    frappe.local.flags.hotel_api_request = True
    form = frappe.local.form_dict
    for key, value in params.items():
        form[key] = value
    form["cmd"] = f"hotel_erp.api.v1.{fn_name}"


def unwrap_v1(response, request):
    if not frappe.local.flags.get("hotel_api_request"):
        return response
    try:
        body = json.loads(response.get_data(as_text=True))
    except (ValueError, TypeError):
        return response
    if isinstance(body, dict) and "message" in body:
        response.set_data(json.dumps(body["message"]))
        response.mimetype = "application/json"
    return response
