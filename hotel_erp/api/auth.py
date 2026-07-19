"""Custom bearer-token authentication (contract §4.2), wired via Frappe's
`auth_hooks` extension point.

Frappe's own `frappe.auth.validate_auth()` intercepts every 2-part
`Authorization` header itself: it first tries the header as a native OAuth2
bearer token (`OAuth Bearer Token` doctype) or as `basic`/`token`-scheme API
key+secret, and if neither matches, raises `frappe.AuthenticationError`
*before* any whitelisted method -- including this app's own
`hotel_erp.api.common._check_bearer()` -- ever runs. A static
`Authorization: Bearer <api_key>` token, the scheme the contract actually
specifies, therefore never reaches application code unless it's handled at
this same layer. `auth_hooks` (called from `validate_auth_via_hooks()`,
after the built-in checks and before the final "still Guest -> raise"
check) is exactly Frappe's documented extension point for this.

Authenticates as the dedicated "Hotel API" service user (created in
`hotel_erp.setup.install.after_install`), never as Administrator -- using
Administrator here would silently bypass the Guest DocType's permission
boundary (NFR-A9/§5.6) for every Aggregator-authenticated request, which
would defeat the whole point of that boundary.
"""
from __future__ import annotations

import hmac

import frappe

SERVICE_USER = "hotel-api@service.local"


def validate_bearer_token() -> None:
    if frappe.session.user not in ("", "Guest"):
        return  # already authenticated via some other mechanism

    header = frappe.get_request_header("Authorization") or ""
    if not header.startswith("Bearer "):
        return
    token = header[len("Bearer "):].strip()
    if not token:
        return

    configured = (
        frappe.utils.password.get_decrypted_password(
            "Sync Config", "Sync Config", "aggregator_api_key", raise_exception=False
        )
        if frappe.db.exists("Sync Config", "Sync Config")
        else None
    )
    if not configured:
        return  # not yet onboarded -- leave enforcement to _check_bearer()'s soft path

    if hmac.compare_digest(token, configured):
        frappe.set_user(SERVICE_USER)
