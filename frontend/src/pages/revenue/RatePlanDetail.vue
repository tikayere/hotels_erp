<template>
  <div class="max-w-4xl space-y-6">
    <RouterLink :to="{ name: 'RatePlans' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('revenueDetail.backLink') }}
    </RouterLink>

    <p v-if="plan.error" class="text-sm text-red-600">{{ plan.error.messages?.[0] || $t('revenueDetail.failedToLoad') }}</p>
    <div v-if="plan.loading && !plan.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="plan.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ plan.data.room_type }} · {{ plan.data.code }}</div>
          <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ plan.data.plan_name }}</div>
        </div>
        <span v-if="plan.data.active" class="text-sm font-medium text-green-600 dark:text-green-400">{{ $t('status.active') }}</span>
        <span v-else class="text-sm text-gray-400">{{ $t('revenue.inactive') }}</span>
      </div>

      <Card :title="$t('revenueDetail.settingsTitle')">
        <div class="flex flex-wrap items-end gap-3">
          <Field :label="$t('revenue.basePriceField')">
            <input v-model.number="basePrice" type="number" min="0" class="input-field w-40" />
          </Field>
          <label class="mb-1.5 flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
            <input v-model="planActive" type="checkbox" class="rounded border-gray-300" />
            {{ $t('status.active') }}
          </label>
          <Button variant="outline" :loading="updatePlan.loading" @click="saveSettings">{{ $t('common.save') }}</Button>
          <Button variant="outline" :loading="recalc.loading" @click="doRecalculate">{{ $t('revenueDetail.recalculateBtn') }}</Button>
        </div>
        <p v-if="updatePlan.error" class="mt-2 text-sm text-red-600">{{ updatePlan.error.messages?.[0] }}</p>
        <p v-if="recalcMessage" class="mt-2 text-sm text-green-600 dark:text-green-400">{{ recalcMessage }}</p>
      </Card>

      <Card :title="$t('revenueDetail.pricingRulesTitle')">
        <template #actions>
          <Button size="sm" variant="outline" @click="openNewRule">{{ $t('revenueDetail.newRuleBtn') }}</Button>
        </template>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-100 text-sm dark:divide-gray-800">
            <thead>
              <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                <th class="py-2 pr-3">{{ $t('revenueDetail.ruleNameCol') }}</th>
                <th class="py-2 pr-3">{{ $t('revenueDetail.ruleTypeCol') }}</th>
                <th class="py-2 pr-3">{{ $t('revenueDetail.adjustmentCol') }}</th>
                <th class="py-2 pr-3">{{ $t('revenueDetail.priorityCol') }}</th>
                <th class="py-2 pr-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-800/60">
              <tr v-if="!plan.data.pricing_rules?.length">
                <td class="py-3 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('revenueDetail.noRules') }}</td>
              </tr>
              <tr v-for="r in plan.data.pricing_rules" :key="r.name">
                <td class="py-2 pr-3 font-medium text-gray-900 dark:text-gray-100">{{ r.rule_name }}</td>
                <td class="py-2 pr-3 text-gray-700 dark:text-gray-300">{{ statusLabel(r.rule_type) }}</td>
                <td class="py-2 pr-3 text-gray-700 dark:text-gray-300">
                  {{ r.adjustment_type === 'percentage' ? `${r.adjustment_value > 0 ? '+' : ''}${r.adjustment_value}%` : r.adjustment_value }}
                </td>
                <td class="py-2 pr-3 text-gray-500 dark:text-gray-400">{{ r.priority }}</td>
                <td class="py-2 pr-3 text-right">
                  <div class="flex justify-end gap-2">
                    <button class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100" @click="openEditRule(r)">
                      {{ $t('common.edit') }}
                    </button>
                    <button class="text-xs text-red-500 hover:text-red-700" @click="doDeleteRule(r.name)">
                      {{ $t('common.delete') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <Card :title="$t('revenueDetail.rateCalendarTitle')">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-100 text-sm dark:divide-gray-800">
            <thead>
              <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                <th class="py-2 pr-3">{{ $t('revenueDetail.dateCol') }}</th>
                <th class="py-2 pr-3 text-right">{{ $t('revenueDetail.priceCol') }}</th>
                <th class="py-2 pr-3">{{ $t('revenueDetail.currencyCol') }}</th>
                <th class="py-2 pr-3 text-right">{{ $t('revenueDetail.roomsAvailableCol') }}</th>
                <th class="py-2 pr-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-800/60">
              <tr v-if="!calendar.data?.rows?.length">
                <td class="py-3 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('revenueDetail.noCalendarRows') }}</td>
              </tr>
              <tr v-for="row in calendar.data?.rows || []" :key="row.date">
                <td class="py-2 pr-3 text-gray-900 dark:text-gray-100">{{ formatDate(row.date) }}</td>
                <td class="py-2 pr-3 text-right">
                  <input v-model.number="editRow[row.date].price_minor" type="number" min="0" class="input-field w-28 text-right" />
                </td>
                <td class="py-2 pr-3">
                  <input v-model="editRow[row.date].currency" type="text" class="input-field w-16" />
                </td>
                <td class="py-2 pr-3 text-right">
                  <input v-model.number="editRow[row.date].rooms_available" type="number" min="0" class="input-field w-20 text-right" />
                </td>
                <td class="py-2 pr-3 text-right">
                  <button class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100" @click="saveCalendarRow(row.date)">
                    {{ $t('common.save') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="upsertRow.error" class="mt-2 text-sm text-red-600">{{ upsertRow.error.messages?.[0] }}</p>
      </Card>
    </template>

    <Dialog v-model="ruleDialogOpen" :options="{ title: editingRule ? $t('revenueDetail.editRuleDialogTitle') : $t('revenueDetail.newRuleDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('revenueDetail.ruleNameField')">
            <input v-model="ruleForm.rule_name" type="text" class="input-field" />
          </Field>
          <Field :label="$t('revenueDetail.ruleTypeCol')">
            <select v-model="ruleForm.rule_type" class="select-field w-full">
              <option v-for="t in RULE_TYPES" :key="t" :value="t">{{ statusLabel(t) }}</option>
            </select>
          </Field>

          <div v-if="['season', 'holiday'].includes(ruleForm.rule_type)" class="grid grid-cols-2 gap-3">
            <Field :label="$t('revenueDetail.startDateField')">
              <input v-model="ruleForm.start_date" type="date" class="input-field" />
            </Field>
            <Field :label="$t('revenueDetail.endDateField')">
              <input v-model="ruleForm.end_date" type="date" class="input-field" />
            </Field>
          </div>

          <Field v-if="ruleForm.rule_type === 'day_of_week'" :label="$t('revenueDetail.daysOfWeekField')">
            <div class="flex flex-wrap gap-2">
              <label v-for="(d, idx) in DAY_LABELS" :key="idx" class="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-300">
                <input type="checkbox" :checked="ruleForm.days_of_week.includes(idx)" class="rounded border-gray-300" @change="toggleDay(idx)" />
                {{ d }}
              </label>
            </div>
          </Field>

          <div v-if="ruleForm.rule_type === 'lead_time'" class="grid grid-cols-2 gap-3">
            <Field :label="$t('revenueDetail.leadMinField')">
              <input v-model.number="ruleForm.lead_time_days_min" type="number" min="0" class="input-field" />
            </Field>
            <Field :label="$t('revenueDetail.leadMaxField')">
              <input v-model.number="ruleForm.lead_time_days_max" type="number" min="0" class="input-field" />
            </Field>
          </div>

          <Field v-if="ruleForm.rule_type === 'occupancy'" :label="$t('revenueDetail.occupancyThresholdField')">
            <input v-model.number="ruleForm.occupancy_threshold_percent" type="number" min="0" class="input-field" />
          </Field>

          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('revenueDetail.adjustmentTypeField')">
              <select v-model="ruleForm.adjustment_type" class="select-field w-full">
                <option value="percentage">{{ $t('revenueDetail.percentage') }}</option>
                <option value="fixed_amount">{{ $t('revenueDetail.fixedAmount') }}</option>
              </select>
            </Field>
            <Field :label="$t('revenueDetail.adjustmentValueField')">
              <input v-model.number="ruleForm.adjustment_value" type="number" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('revenueDetail.priorityCol')">
            <input v-model.number="ruleForm.priority" type="number" class="input-field w-24" />
          </Field>
        </div>
        <p v-if="ruleError" class="mt-3 text-sm text-red-600">{{ ruleError }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="ruleDialogOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!ruleForm.rule_name" :loading="ruleSaving" @click="saveRule">{{ $t('common.save') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  createPricingRuleResource,
  deletePricingRuleResource,
  rateCalendarResource,
  ratePlanResource,
  recalculateNowResource,
  updatePricingRuleResource,
  updateRatePlanResource,
  upsertRateCalendarRowResource,
} from '@/api/revenue'
import { formatDate, statusLabel } from '@/utils/format'
import Field from '@/components/Field.vue'
import Card from '@/components/Card.vue'

const props = defineProps({ id: { type: String, required: true } })

const RULE_TYPES = ['season', 'holiday', 'day_of_week', 'lead_time', 'occupancy']
// days_of_week is stored Python-weekday convention (Monday=0..Sunday=6, see
// pricing/rules.py's docstring) -- these labels are indexed the same way.
const { t } = useI18n()
const DAY_LABELS = computed(() => [
  t('revenueDetail.mon'), t('revenueDetail.tue'), t('revenueDetail.wed'), t('revenueDetail.thu'),
  t('revenueDetail.fri'), t('revenueDetail.sat'), t('revenueDetail.sun'),
])

const plan = ratePlanResource()
const calendar = rateCalendarResource()
const updatePlan = updateRatePlanResource()
const createRule = createPricingRuleResource()
const updateRule = updatePricingRuleResource()
const deleteRule = deletePricingRuleResource()
const upsertRow = upsertRateCalendarRowResource()
const recalc = recalculateNowResource()

const basePrice = ref(null)
const planActive = ref(true)
const recalcMessage = ref('')

function load() {
  plan.fetch(
    { name: props.id },
    {
      onSuccess: (d) => {
        basePrice.value = d.base_price_minor
        planActive.value = !!d.active
      },
    },
  )
  calendar.fetch({ rate_plan: props.id })
}
onMounted(load)
watch(() => props.id, load)

function saveSettings() {
  updatePlan.submit(
    { name: props.id, base_price_minor: basePrice.value, active: planActive.value ? 1 : 0 },
    { onSuccess: load },
  )
}
function doRecalculate() {
  recalcMessage.value = ''
  recalc.submit({}, { onSuccess: () => { recalcMessage.value = '✓'; load() } })
}

const editRow = reactive({})
watch(
  () => calendar.data,
  (d) => {
    Object.keys(editRow).forEach((k) => delete editRow[k])
    for (const row of d?.rows || []) {
      editRow[row.date] = { price_minor: row.price_minor, currency: row.currency, rooms_available: row.rooms_available }
    }
  },
)
function saveCalendarRow(date) {
  const r = editRow[date]
  upsertRow.submit(
    { rate_plan: props.id, date, price_minor: r.price_minor, currency: r.currency, rooms_available: r.rooms_available },
    { onSuccess: () => calendar.fetch({ rate_plan: props.id }) },
  )
}

const ruleDialogOpen = ref(false)
const editingRule = ref(null)
const ruleForm = reactive({
  rule_name: '', rule_type: 'season', start_date: '', end_date: '', days_of_week: [],
  lead_time_days_min: null, lead_time_days_max: null, occupancy_threshold_percent: null,
  adjustment_type: 'percentage', adjustment_value: 0, priority: 0,
})
const ruleSaving = computed(() => createRule.loading || updateRule.loading)
const ruleError = computed(() => createRule.error?.messages?.[0] || updateRule.error?.messages?.[0])

function resetRuleForm() {
  Object.assign(ruleForm, {
    rule_name: '', rule_type: 'season', start_date: '', end_date: '', days_of_week: [],
    lead_time_days_min: null, lead_time_days_max: null, occupancy_threshold_percent: null,
    adjustment_type: 'percentage', adjustment_value: 0, priority: 0,
  })
}
function openNewRule() {
  editingRule.value = null
  resetRuleForm()
  createRule.error = null
  ruleDialogOpen.value = true
}
function openEditRule(r) {
  editingRule.value = r
  Object.assign(ruleForm, {
    rule_name: r.rule_name, rule_type: r.rule_type, start_date: r.start_date || '', end_date: r.end_date || '',
    days_of_week: Array.isArray(r.days_of_week) ? r.days_of_week : [],
    lead_time_days_min: r.lead_time_days_min, lead_time_days_max: r.lead_time_days_max,
    occupancy_threshold_percent: r.occupancy_threshold_percent,
    adjustment_type: r.adjustment_type, adjustment_value: r.adjustment_value, priority: r.priority,
  })
  updateRule.error = null
  ruleDialogOpen.value = true
}
function toggleDay(idx) {
  const i = ruleForm.days_of_week.indexOf(idx)
  if (i === -1) ruleForm.days_of_week.push(idx)
  else ruleForm.days_of_week.splice(i, 1)
}
function saveRule() {
  const payload = {
    rate_plan: props.id,
    rule_name: ruleForm.rule_name,
    rule_type: ruleForm.rule_type,
    start_date: ruleForm.start_date || undefined,
    end_date: ruleForm.end_date || undefined,
    days_of_week: ruleForm.rule_type === 'day_of_week' ? ruleForm.days_of_week : undefined,
    lead_time_days_min: ruleForm.lead_time_days_min ?? undefined,
    lead_time_days_max: ruleForm.lead_time_days_max ?? undefined,
    occupancy_threshold_percent: ruleForm.occupancy_threshold_percent ?? undefined,
    adjustment_type: ruleForm.adjustment_type,
    adjustment_value: ruleForm.adjustment_value,
    priority: ruleForm.priority,
  }
  if (editingRule.value) {
    updateRule.submit({ name: editingRule.value.name, ...payload }, { onSuccess: () => { ruleDialogOpen.value = false; load() } })
  } else {
    createRule.submit(payload, { onSuccess: () => { ruleDialogOpen.value = false; load() } })
  }
}
function doDeleteRule(name) {
  deleteRule.submit({ name }, { onSuccess: load })
}
</script>
