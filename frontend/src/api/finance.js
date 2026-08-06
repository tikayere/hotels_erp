// createResource factories over hotel_erp.api.finance — see
// erp/hotel_erp/api/finance.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.finance.${fn}`

export const txnsResource = () => createResource({ url: M('list_txns'), auto: false })
export const createTxnResource = () => createResource({ url: M('create_txn'), auto: false })
export const submitTxnResource = () => createResource({ url: M('submit_txn'), auto: false })
export const cancelTxnResource = () => createResource({ url: M('cancel_txn'), auto: false })
export const financeSummaryResource = () => createResource({ url: M('get_summary'), auto: false })
