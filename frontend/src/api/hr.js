// createResource factories over hotel_erp.api.hr — see erp/hotel_erp/api/hr.py
// for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.hr.${fn}`

export const staffListResource = () => createResource({ url: M('list_staff'), auto: false })
export const staffResource = () => createResource({ url: M('get_staff'), auto: false })
export const createStaffResource = () => createResource({ url: M('create_staff'), auto: false })
export const updateStaffResource = () => createResource({ url: M('update_staff'), auto: false })

export const leaveApplicationsResource = () =>
  createResource({ url: M('list_leave_applications'), auto: false })
export const createLeaveApplicationResource = () =>
  createResource({ url: M('create_leave_application'), auto: false })
export const approveLeaveResource = () => createResource({ url: M('approve_leave'), auto: false })
export const rejectLeaveResource = () => createResource({ url: M('reject_leave'), auto: false })

export const payrollEntriesResource = () => createResource({ url: M('list_payroll_entries'), auto: false })
export const generatePayrollResource = () => createResource({ url: M('generate_payroll'), auto: false })
export const processPayrollResource = () => createResource({ url: M('process_payroll'), auto: false })
export const payPayrollResource = () => createResource({ url: M('pay_payroll'), auto: false })
