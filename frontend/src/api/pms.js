// Thin `createResource` factories over `hotel_erp.api.pms` (the SPA's
// session-authenticated internal API — see erp/hotel_erp/api/pms.py for the
// server side of every one of these). Kept in one place so every page calls
// the same method names/params rather than re-typing dotted URLs.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.pms.${fn}`

export function dashboardResource() {
  return createResource({ url: M('get_dashboard'), auto: false })
}

export function roomsResource() {
  return createResource({ url: M('list_rooms'), auto: false })
}

export function availableRoomsResource() {
  return createResource({ url: M('list_available_rooms'), auto: false })
}

export function roomTypesResource() {
  return createResource({ url: M('list_room_types'), auto: false })
}

export function availabilityResource() {
  return createResource({ url: M('get_availability'), auto: false })
}

export function reservationsResource() {
  return createResource({ url: M('list_reservations'), auto: false })
}

export function reservationResource() {
  return createResource({ url: M('get_reservation'), auto: false })
}

export function checkInResource() {
  return createResource({ url: M('check_in_reservation'), auto: false })
}

export function checkOutResource() {
  return createResource({ url: M('check_out_reservation'), auto: false })
}

export function cancelReservationResource() {
  return createResource({ url: M('cancel_reservation'), auto: false })
}

// Walk-in booking: hotel_erp.api.pms.create_walkin_reservation wraps
// hotel_erp.booking.direct_sale (same atomic-hold/inventory/event path an
// Aggregator hold uses, FR-A18) and reshapes the response to the bare-ID
// shape every other method on this page uses.
export function createWalkinReservationResource() {
  return createResource({
    url: M('create_walkin_reservation'),
    auto: false,
  })
}
