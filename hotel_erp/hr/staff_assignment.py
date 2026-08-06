"""Least-loaded active-staff picker, shared by every internal module that
auto-assigns work to a department (housekeeping checkout tasks, kitchen
order routing). Deliberately simple round-robin-by-current-load rather than
skill/shift-aware scheduling -- that's a real PMS feature, this is the
"internal-only, build per usual Frappe conventions" scope the contract's
own FR-A8-A15 note allows (phase_2 §... "internal module workflows").
"""
from __future__ import annotations

import frappe


def pick_least_loaded_staff(
    department: str,
    open_task_doctype: str,
    assignee_field: str,
    open_status_field: str,
    open_statuses: list[str],
) -> str | None:
    """Returns the `User` of the active staff member in `department` with a
    linked User account and currently the fewest open records in
    `open_task_doctype`, or None if no such staff exist. `assigned_to` on
    both Housekeeping Task and Restaurant Order is a Link to `User` (so a
    login-capable staff member can see their own queue), not to `Staff` --
    an active Staff row with no linked User is real (not every employee
    needs Desk access) but can't be assigned to, so it's excluded here
    rather than producing an invalid link.

    "Open" is caller-defined (`open_status_field` in `open_statuses`) since
    Housekeeping Task and Restaurant Order use different status vocabularies.
    """
    staff = frappe.get_all(
        "Staff",
        filters={"department": department, "status": "active", "user": ["is", "set"]},
        fields=["name", "user"],
    )
    if not staff:
        return None

    load = {s.name: 0 for s in staff}
    user_to_staff = {s.user: s.name for s in staff if s.user}

    open_rows = frappe.get_all(
        open_task_doctype,
        filters={open_status_field: ["in", open_statuses]},
        fields=[assignee_field],
    )
    for row in open_rows:
        assignee = row.get(assignee_field)
        staff_name = user_to_staff.get(assignee)
        if staff_name is not None:
            load[staff_name] += 1

    # min() over frappe.get_all's result preserves its natural (creation)
    # order on ties, so this is a stable round-robin among equally-loaded
    # staff, not just "whoever sorts first alphabetically".
    least_loaded = min(staff, key=lambda s: load[s.name])
    return least_loaded.user
