<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Payroll</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">All statuses</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <Button variant="solid" @click="genOpen = true">Run Payroll</Button>
      </div>
    </div>

    <p v-if="entries.error" class="text-sm text-red-600">{{ entries.error.messages?.[0] || 'Failed to load' }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">Staff</th>
            <th class="px-4 py-3">Period</th>
            <th class="px-4 py-3 text-right">Gross</th>
            <th class="px-4 py-3 text-right">Deductions</th>
            <th class="px-4 py-3 text-right">Net</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="entries.loading && !entries.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="7">Loading…</td>
          </tr>
          <tr v-else-if="!entries.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="7">No payroll entries yet.</td>
          </tr>
          <tr v-for="e in entries.data" :key="e.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ e.staff_name }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDate(e.pay_period_start) }} → {{ formatDate(e.pay_period_end) }}</td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{{ formatMoney(e.gross_amount_minor, e.currency) }}</td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{{ formatMoney(e.deductions_minor, e.currency) }}</td>
            <td class="px-4 py-3 text-right font-medium text-gray-900 dark:text-gray-100">{{ formatMoney(e.net_amount_minor, e.currency) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="e.status" /></td>
            <td class="px-4 py-3 text-right">
              <Button v-if="e.status === 'draft'" size="sm" variant="outline" @click="doProcess(e.name)">Process</Button>
              <Button v-else-if="e.status === 'processed'" size="sm" variant="outline" theme="green" @click="doPay(e.name)">
                Mark Paid
              </Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="genOpen" :options="{ title: 'Run Payroll' }">
      <template #body-content>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <Field label="Period Start">
              <input v-model="genForm.pay_period_start" type="date" class="input-field" />
            </Field>
            <Field label="Period End">
              <input v-model="genForm.pay_period_end" type="date" class="input-field" />
            </Field>
          </div>
          <Field label="Currency">
            <input v-model="genForm.currency" type="text" placeholder="USD" class="input-field" />
          </Field>
          <Field label="Deduction Rate (0–1)">
            <input v-model.number="genForm.deduction_rate" type="number" step="0.01" min="0" max="1" class="input-field" />
          </Field>
        </div>
        <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
          Creates one draft entry per active staff member with a daily rate set, skipping anyone who
          already has an entry for this period.
        </p>
        <p v-if="generatePayroll.error" class="mt-2 text-sm text-red-600">{{ generatePayroll.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="genOpen = false">Cancel</Button>
          <Button
            variant="solid"
            :disabled="!genForm.pay_period_start || !genForm.pay_period_end || !genForm.currency"
            :loading="generatePayroll.loading"
            @click="runPayroll"
          >
            Generate
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { generatePayrollResource, payPayrollResource, payrollEntriesResource, processPayrollResource } from '@/api/hr'
import { formatDate, formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['draft', 'processed', 'paid']

const statusFilter = ref('')
const entries = payrollEntriesResource()
const generatePayroll = generatePayrollResource()
const processPayroll = processPayrollResource()
const payPayroll = payPayrollResource()

const genOpen = ref(false)
const genForm = reactive({ pay_period_start: '', pay_period_end: '', currency: 'USD', deduction_rate: 0.1 })

function load() {
  entries.fetch({ status: statusFilter.value || undefined })
}
onMounted(load)
watch(statusFilter, load)

function runPayroll() {
  generatePayroll.submit(
    { ...genForm },
    { onSuccess: () => { genOpen.value = false; load() } },
  )
}

function doProcess(name) {
  processPayroll.submit({ name }, { onSuccess: load })
}
function doPay(name) {
  payPayroll.submit({ name }, { onSuccess: load })
}
</script>
