// createResource factories over hotel_erp.api.maintenance — see
// erp/hotel_erp/api/maintenance.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.maintenance.${fn}`

export const requestsResource = () => createResource({ url: M('list_requests'), auto: false })
export const requestResource = () => createResource({ url: M('get_request'), auto: false })
export const createRequestResource = () => createResource({ url: M('create_request'), auto: false })
export const assignRequestResource = () => createResource({ url: M('assign_request'), auto: false })
export const startRequestResource = () => createResource({ url: M('start_request'), auto: false })
export const resolveRequestResource = () => createResource({ url: M('resolve_request'), auto: false })
export const closeRequestResource = () => createResource({ url: M('close_request'), auto: false })
