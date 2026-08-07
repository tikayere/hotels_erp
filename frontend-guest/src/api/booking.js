// createResource factories over hotel_erp.api.public_booking — see
// erp/hotel_erp/api/public_booking.py for the server side of each of these.
// Every call here is unauthenticated (allow_guest=True on the server); no
// session/login is required or assumed anywhere in this app.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.public_booking.${fn}`

export const portalSettingsResource = () => createResource({ url: M('get_portal_settings'), auto: false })
export const roomTypesResource = () => createResource({ url: M('list_room_types'), auto: false })
export const availabilityResource = () => createResource({ url: M('check_availability'), auto: false })
export const createBookingResource = () => createResource({ url: M('create_booking'), auto: false })
export const getBookingResource = () => createResource({ url: M('get_booking'), auto: false })
