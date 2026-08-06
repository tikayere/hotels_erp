// createResource factories over hotel_erp.api.restaurant — see
// erp/hotel_erp/api/restaurant.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.restaurant.${fn}`

export const ordersResource = () => createResource({ url: M('list_orders'), auto: false })
export const orderResource = () => createResource({ url: M('get_order'), auto: false })
export const createOrderResource = () => createResource({ url: M('create_order'), auto: false })
export const advanceOrderResource = () => createResource({ url: M('advance_order'), auto: false })
export const cancelOrderResource = () => createResource({ url: M('cancel_order'), auto: false })
