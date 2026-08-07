// createResource factories over hotel_erp.api.analytics -- see
// erp/hotel_erp/api/analytics.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.analytics.${fn}`

export const kpiSummaryResource = () => createResource({ url: M('get_kpi_summary'), auto: false })
export const occupancyTrendResource = () => createResource({ url: M('get_occupancy_trend'), auto: false })
export const revenueTrendResource = () => createResource({ url: M('get_revenue_trend'), auto: false })
export const adrRevparTrendResource = () => createResource({ url: M('get_adr_revpar_trend'), auto: false })
