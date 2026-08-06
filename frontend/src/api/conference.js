// createResource factories over hotel_erp.api.conference — see
// erp/hotel_erp/api/conference.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.conference.${fn}`

export const bookingsResource = () => createResource({ url: M('list_bookings'), auto: false })
export const createBookingResource = () => createResource({ url: M('create_booking'), auto: false })
export const confirmBookingResource = () => createResource({ url: M('confirm_booking'), auto: false })
export const cancelBookingResource = () => createResource({ url: M('cancel_booking'), auto: false })
