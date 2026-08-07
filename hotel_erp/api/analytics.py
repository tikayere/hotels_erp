"""Session-authenticated internal API for the Analytics module of the `/pms`
SPA -- occupancy, ADR/RevPAR, and revenue trend data for an in-app dashboard
with charts. Previously this data only existed as Desk Query Reports
(`analytics/report/*.json`) -- a real hotel manager wants a chart on login,
not a spreadsheet-style report navigated to separately (ENTERPRISE_READINESS_PLAN.md
Wave D). The SQL here deliberately mirrors those existing reports' queries
(same joins, same exclusion of cancelled/no_show) rather than diverging, so
the two stay consistent if either is read side-by-side with the other.

Restricted to `pms_common.REVENUE_ROLES`, same audience as those reports'
own `roles` blocks (System Manager + Revenue Manager).
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate

from hotel_erp.api.pms_common import require_revenue_role


def _property_room_type_filter(property):
    if not property:
        return "", {}
    return "AND rt.property = %(property)s", {"property": property}


@frappe.whitelist()
def get_occupancy_trend(property=None, days=30):
    require_revenue_role()
    days = min(365, max(1, int(days or 30)))
    end = getdate()
    start = add_days(end, -(days - 1))
    prop_clause, prop_values = _property_room_type_filter(property)

    booked_by_date = {
        str(row["date"]): row["rooms_booked"]
        for row in frappe.db.sql(
            f"""
            SELECT r.check_in AS date, SUM(r.rooms_requested) AS rooms_booked
            FROM `tabReservation` r
            JOIN `tabRoom Type` rt ON rt.name = r.room_type
            WHERE r.status NOT IN ('cancelled', 'no_show')
              AND r.check_in BETWEEN %(start)s AND %(end)s
              {prop_clause}
            GROUP BY r.check_in
            """,
            {"start": start, "end": end, **prop_values},
            as_dict=True,
        )
    }

    room_where = "WHERE property = %(property)s" if property else ""
    total_rooms = frappe.db.sql(
        f"SELECT COUNT(name) AS n FROM `tabRoom` {room_where}",
        {"property": property},
        as_dict=True,
    )[0]["n"] or 0

    rows = []
    d = start
    while d <= end:
        booked = booked_by_date.get(str(d), 0) or 0
        rows.append({
            "date": str(d),
            "rooms_booked": booked,
            "rooms_total": total_rooms,
            "occupancy_percent": round(booked / total_rooms * 100, 1) if total_rooms else 0,
        })
        d = add_days(d, 1)
    return rows


@frappe.whitelist()
def get_revenue_trend(property=None, days=30):
    require_revenue_role()
    days = min(365, max(1, int(days or 30)))
    end = getdate()
    start = add_days(end, -(days - 1))

    # Finance Txn has no property field (a ledger row is scoped to a
    # reservation, not a property directly) -- when a property filter is
    # requested, join through Reservation -> Room Type for the ones that
    # have a reservation link; standalone (non-reservation) txns are
    # necessarily excluded from a property-scoped view since they can't be
    # attributed to one.
    if property:
        room_types = frappe.get_all("Room Type", filters={"property": property}, pluck="name")
        if not room_types:
            room_types = [""]
        rows = frappe.db.sql(
            """
            SELECT DATE(ft.creation) AS date,
                   SUM(CASE WHEN ft.type = 'revenue' THEN ft.amount_minor ELSE 0 END) AS revenue_minor,
                   SUM(CASE WHEN ft.type = 'refund' THEN ft.amount_minor ELSE 0 END) AS refund_minor,
                   SUM(CASE WHEN ft.type = 'payment' THEN ft.amount_minor ELSE 0 END) AS payment_minor,
                   MAX(ft.currency) AS currency
            FROM `tabFinance Txn` ft
            JOIN `tabReservation` r ON r.name = ft.reservation
            JOIN `tabRoom Type` rt ON rt.name = r.room_type
            WHERE ft.docstatus = 1 AND DATE(ft.creation) BETWEEN %(start)s AND %(end)s
              AND rt.property = %(property)s
            GROUP BY DATE(ft.creation)
            """,
            {"start": start, "end": end, "property": property},
            as_dict=True,
        )
    else:
        rows = frappe.db.sql(
            """
            SELECT DATE(creation) AS date,
                   SUM(CASE WHEN type = 'revenue' THEN amount_minor ELSE 0 END) AS revenue_minor,
                   SUM(CASE WHEN type = 'refund' THEN amount_minor ELSE 0 END) AS refund_minor,
                   SUM(CASE WHEN type = 'payment' THEN amount_minor ELSE 0 END) AS payment_minor,
                   MAX(currency) AS currency
            FROM `tabFinance Txn`
            WHERE docstatus = 1 AND DATE(creation) BETWEEN %(start)s AND %(end)s
            GROUP BY DATE(creation)
            """,
            {"start": start, "end": end},
            as_dict=True,
        )
    by_date = {str(r["date"]): r for r in rows}

    # Deployments here run one currency in practice (confirmed by the
    # existing ADR/RevPAR Query Report, which sums total_amount_minor across
    # reservations without a currency GROUP BY at all -- multi-currency is
    # out of scope per contract §6) -- pick the first non-null currency seen
    # in the window as the series' currency rather than repeating a MAX()
    # per-row, same "first wins" simplification api/finance.py's
    # get_summary() already uses.
    series_currency = next((r["currency"] for r in rows if r["currency"]), None)

    out = []
    d = start
    while d <= end:
        r = by_date.get(str(d))
        out.append({
            "date": str(d),
            "revenue_minor": (r["revenue_minor"] if r else 0) or 0,
            "refund_minor": (r["refund_minor"] if r else 0) or 0,
            "payment_minor": (r["payment_minor"] if r else 0) or 0,
            "currency": series_currency,
        })
        d = add_days(d, 1)
    return out


@frappe.whitelist()
def get_adr_revpar_trend(property=None, days=30):
    """Average Daily Rate and Revenue Per Available Room, by check-in date --
    same formula as the `ADR and RevPAR` Query Report (`analytics/report/
    adr_and_revpar/`), just windowed to the trailing `days` and returned as
    JSON for a chart instead of a Desk report grid."""
    require_revenue_role()
    days = min(365, max(1, int(days or 30)))
    end = getdate()
    start = add_days(end, -(days - 1))
    prop_clause, prop_values = _property_room_type_filter(property)

    rows = frappe.db.sql(
        f"""
        SELECT
            r.check_in AS date,
            ROUND(SUM(r.total_amount_minor) / NULLIF(SUM(r.rooms_requested), 0)) AS adr_minor,
            ROUND(SUM(r.total_amount_minor) / NULLIF(
                (SELECT COUNT(*) FROM `tabRoom` room WHERE room.room_type = r.room_type), 0
            )) AS revpar_minor,
            MAX(r.currency) AS currency
        FROM `tabReservation` r
        JOIN `tabRoom Type` rt ON rt.name = r.room_type
        WHERE r.status NOT IN ('cancelled', 'no_show')
          AND r.check_in BETWEEN %(start)s AND %(end)s
          {prop_clause}
        GROUP BY r.check_in
        ORDER BY r.check_in
        """,
        {"start": start, "end": end, **prop_values},
        as_dict=True,
    )
    for r in rows:
        r["date"] = str(r["date"])
        r["adr_minor"] = r["adr_minor"] or 0
        r["revpar_minor"] = r["revpar_minor"] or 0
    return rows


@frappe.whitelist()
def get_kpi_summary(property=None):
    """Snapshot KPIs for the top of the Analytics page -- today's occupancy,
    trailing-30-day ADR/RevPAR, and month-to-date revenue."""
    require_revenue_role()
    today = getdate()
    month_start = today.replace(day=1)

    occ_today = get_occupancy_trend(property=property, days=1)[0]

    adr_rows = get_adr_revpar_trend(property=property, days=30)
    adr_values = [r["adr_minor"] for r in adr_rows if r["adr_minor"]]
    revpar_values = [r["revpar_minor"] for r in adr_rows if r["revpar_minor"]]
    avg_adr = round(sum(adr_values) / len(adr_values)) if adr_values else 0
    avg_revpar = round(sum(revpar_values) / len(revpar_values)) if revpar_values else 0
    currency = next((r["currency"] for r in adr_rows if r["currency"]), None)

    rev_rows = get_revenue_trend(property=property, days=(today - month_start).days + 1)
    mtd_revenue = sum(r["revenue_minor"] for r in rev_rows)
    currency = currency or next((r["currency"] for r in rev_rows if r["currency"]), None)

    return {
        "occupancy_percent_today": occ_today["occupancy_percent"],
        "rooms_booked_today": occ_today["rooms_booked"],
        "rooms_total": occ_today["rooms_total"],
        "avg_adr_minor_30d": avg_adr,
        "avg_revpar_minor_30d": avg_revpar,
        "mtd_revenue_minor": mtd_revenue,
        "currency": currency,
    }
