// Tiny module-level store (no Pinia needed for a 4-page site).
//
// `lastBooking` carries the just-created reservation from Book.vue straight
// to Confirmation.vue in memory, avoiding a round-trip back to the server
// for the common case. It does NOT survive a hard refresh/new tab — that's
// fine, Confirmation.vue falls back to `hotel_erp.api.public_booking.
// get_booking(confirmation_number, email)` (same lookup Lookup.vue uses)
// whenever the store is empty, e.g. from a bookmarked/refreshed link.
//
// `portalSettings` (branding + enabled flag) is fetched once by App.vue on
// mount and read from here by every page that needs the hotel's name/logo/
// address, instead of every page re-fetching it.
import { ref } from 'vue'

export const lastBooking = ref(null)
export const portalSettings = ref(null)

export function formatMoney(minor, currency) {
  if (minor == null) return ''
  const amount = (minor / 100).toFixed(2)
  return currency ? `${amount} ${currency}` : amount
}

export function formatDate(value) {
  if (!value) return ''
  return new Date(value + 'T00:00:00').toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function nightsBetween(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0
  const ms = new Date(checkOut) - new Date(checkIn)
  return Math.max(0, Math.round(ms / (1000 * 60 * 60 * 24)))
}
