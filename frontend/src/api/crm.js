// createResource factories over hotel_erp.api.crm — see erp/hotel_erp/api/crm.py
// for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.crm.${fn}`

export const searchGuestsResource = () => createResource({ url: M('search_guests'), auto: false })
export const guestResource = () => createResource({ url: M('get_guest'), auto: false })

export const createCommunicationResource = () =>
  createResource({ url: M('create_communication'), auto: false })

export const complaintsResource = () => createResource({ url: M('list_complaints'), auto: false })
export const createComplaintResource = () => createResource({ url: M('create_complaint'), auto: false })
export const updateComplaintStatusResource = () =>
  createResource({ url: M('update_complaint_status'), auto: false })
