// createResource factories over hotel_erp.api.inventory — see
// erp/hotel_erp/api/inventory.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.inventory.${fn}`

export const itemsResource = () => createResource({ url: M('list_items'), auto: false })
export const createItemResource = () => createResource({ url: M('create_item'), auto: false })
export const updateItemResource = () => createResource({ url: M('update_item'), auto: false })

export const suppliersResource = () => createResource({ url: M('list_suppliers'), auto: false })
export const createSupplierResource = () => createResource({ url: M('create_supplier'), auto: false })

export const purchaseOrdersResource = () => createResource({ url: M('list_purchase_orders'), auto: false })
export const purchaseOrderResource = () => createResource({ url: M('get_purchase_order'), auto: false })
export const createPurchaseOrderResource = () =>
  createResource({ url: M('create_purchase_order'), auto: false })
export const markOrderedResource = () => createResource({ url: M('mark_ordered'), auto: false })
export const markReceivedResource = () => createResource({ url: M('mark_received'), auto: false })
export const cancelPurchaseOrderResource = () =>
  createResource({ url: M('cancel_purchase_order'), auto: false })
