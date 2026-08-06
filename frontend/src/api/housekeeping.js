// createResource factories over hotel_erp.api.housekeeping — see
// erp/hotel_erp/api/housekeeping.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.housekeeping.${fn}`

export const tasksResource = () => createResource({ url: M('list_tasks'), auto: false })
export const taskResource = () => createResource({ url: M('get_task'), auto: false })
export const createTaskResource = () => createResource({ url: M('create_task'), auto: false })
export const assignTaskResource = () => createResource({ url: M('assign_task'), auto: false })
export const startTaskResource = () => createResource({ url: M('start_task'), auto: false })
export const completeTaskResource = () => createResource({ url: M('complete_task'), auto: false })
export const verifyTaskResource = () => createResource({ url: M('verify_task'), auto: false })
