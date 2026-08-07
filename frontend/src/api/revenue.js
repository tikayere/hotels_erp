// createResource factories over hotel_erp.api.revenue -- see
// erp/hotel_erp/api/revenue.py for the server side of each of these.
import { createResource } from 'frappe-ui'

const M = (fn) => `hotel_erp.api.revenue.${fn}`

export const ratePlansResource = () => createResource({ url: M('list_rate_plans'), auto: false })
export const ratePlanResource = () => createResource({ url: M('get_rate_plan'), auto: false })
export const createRatePlanResource = () => createResource({ url: M('create_rate_plan'), auto: false })
export const updateRatePlanResource = () => createResource({ url: M('update_rate_plan'), auto: false })

export const createPricingRuleResource = () => createResource({ url: M('create_pricing_rule'), auto: false })
export const updatePricingRuleResource = () => createResource({ url: M('update_pricing_rule'), auto: false })
export const deletePricingRuleResource = () => createResource({ url: M('delete_pricing_rule'), auto: false })

export const rateCalendarResource = () => createResource({ url: M('list_rate_calendar'), auto: false })
export const upsertRateCalendarRowResource = () => createResource({ url: M('upsert_rate_calendar_row'), auto: false })
export const recalculateNowResource = () => createResource({ url: M('recalculate_now'), auto: false })
