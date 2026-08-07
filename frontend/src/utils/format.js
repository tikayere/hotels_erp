// Money is always stored/transmitted as integer minor units (cents) + an
// ISO currency code (doctype_spec.md §1.2) — never a float major amount.
import i18n from '@/i18n'

// Follows the app's selected language (LangSwitcher.vue), not just the
// browser's — so a French-speaking front-desk agent gets "7 août 2026"
// even on an English-locale OS/browser, and vice versa.
function intlLocale() {
  return i18n.global.locale.value === 'fr' ? 'fr-FR' : 'en-US'
}

export function formatMoney(minor, currency) {
  if (minor == null || !currency) return '—'
  try {
    return new Intl.NumberFormat(intlLocale(), { style: 'currency', currency }).format(minor / 100)
  } catch {
    return `${(minor / 100).toFixed(2)} ${currency}`
  }
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(`${value}T00:00:00`).toLocaleDateString(intlLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value.replace(' ', 'T')).toLocaleString(intlLocale(), {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function nights(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0
  const ms = new Date(`${checkOut}T00:00:00`) - new Date(`${checkIn}T00:00:00`)
  return Math.max(0, Math.round(ms / 86400000))
}

// Every raw status/type/category/channel value used across every module
// (Reservation, Room, Housekeeping Task, Maintenance Request, Restaurant
// Order, Finance Txn, HR Staff/Leave/Payroll, CRM Communication/Complaint,
// Conference Booking, Inventory Item) — translated via the `status.*`
// namespace in locales/{fr,en}.json rather than a hardcoded English map, so
// switching the app language (see LangSwitcher.vue) relabels every pill and
// dropdown option in one place. Falls back to the raw value for anything
// not yet in the locale files rather than showing a missing-key string.
export function statusLabel(status) {
  const key = `status.${status}`
  return i18n.global.te(key) ? i18n.global.t(key) : status
}

// Same pattern for HR department names (a fixed Select option list, kept in
// English as the underlying stored value — see locales/*.json's
// `departments` namespace — only the on-screen label is translated).
export function departmentLabel(department) {
  const key = `departments.${department}`
  return i18n.global.te(key) ? i18n.global.t(key) : department
}
