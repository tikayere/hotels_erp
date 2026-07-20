"""Retrofits real icons onto the Desk sidebar for sites that installed
hotel_erp before workspace_icons.py existed -- after_install only runs on a
fresh `install-app`, so already-installed sites need this run once via
`bench migrate` instead. See hotel_erp.setup.workspace_icons for why the
icons were missing in the first place."""
from __future__ import annotations

from hotel_erp.setup.workspace_icons import set_sidebar_icons


def execute() -> None:
    set_sidebar_icons()
