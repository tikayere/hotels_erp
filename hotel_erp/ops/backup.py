"""NFR-A7: automated daily backup + retention.

Frappe ships the actual dump mechanism (`frappe.utils.backups.new_backup`,
the same code `bench backup` calls) but nothing that runs it on a schedule
or prunes old sets -- this wires both up. Registered per-site in
`scheduler_events["daily_long"]` (hooks.py), so Frappe's own scheduler runs
it once for every installed site, not just one.

Retention is `backup_retention_days` in that site's `site_config.json`
(falls back to `_DEFAULT_RETENTION_DAYS`) -- deliberately per-site config,
not a hotel_erp setting, since backup storage policy is an infra concern of
whoever deploys a given site, matching this contract item's own framing
("Ops/infra concern, deferred to actual deployment target" -- see
ROADMAP.md) even though the job itself now actually runs by default.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta

import frappe
from frappe.utils.backups import get_backup_path, new_backup

_DEFAULT_RETENTION_DAYS = 7

# Every file in one backup "set" shares this timestamp prefix (see
# BackupGenerator.set_backup_file_name: f"{todays_date}-{site_slug}-...",
# todays_date = now_datetime().strftime("%Y%m%d_%H%M%S")) -- matching on the
# whole prefix, not just today's date, is what keeps a purge atomic per set
# rather than deleting some of a set's files but not others.
_PREFIX_RE = re.compile(r"^(\d{8}_\d{6})-")


def run_daily_backup() -> None:
    # ignore_files=False: back up the site's private/public files (includes
    # Room Type photo uploads) alongside the DB dump, not just the DB --
    # `force=True` skips new_backup's own "skip if last backup < 6h old"
    # throttle, which would otherwise make a *daily* job a no-op every time
    # a manual `bench backup` had run more recently.
    new_backup(ignore_files=False, force=True)
    _purge_old_backups()


def _purge_old_backups() -> None:
    retention_days = frappe.conf.get("backup_retention_days") or _DEFAULT_RETENTION_DAYS
    cutoff = datetime.now() - timedelta(days=retention_days)

    backup_dir = get_backup_path()
    if not os.path.isdir(backup_dir):
        return

    filenames = os.listdir(backup_dir)
    prefixes: dict[str, datetime] = {}
    for filename in filenames:
        match = _PREFIX_RE.match(filename)
        if not match:
            continue
        prefix = match.group(1)
        if prefix not in prefixes:
            try:
                prefixes[prefix] = datetime.strptime(prefix, "%Y%m%d_%H%M%S")
            except ValueError:
                continue

    stale_prefixes = [prefix for prefix, taken_at in prefixes.items() if taken_at < cutoff]
    for filename in filenames:
        if any(filename.startswith(prefix) for prefix in stale_prefixes):
            os.remove(os.path.join(backup_dir, filename))
