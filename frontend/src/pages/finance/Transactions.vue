<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('finance.title') }}</h1>
      <Button variant="solid" @click="openNewTxn">{{ $t('finance.newTransaction') }}</Button>
    </div>

    <div v-if="summary.data" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <KpiCard
        v-for="t in TYPES"
        :key="t"
        :label="statusLabel(t)"
        icon="💰"
        :value="formatMoney(summary.data.by_type[t]?.total_minor, summary.data.by_type[t]?.currency)"
      />
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <select v-model="typeFilter" class="select-field">
        <option value="">{{ $t('common.allStatuses') }}</option>
        <option v-for="t in TYPES" :key="t" :value="t">{{ statusLabel(t) }}</option>
      </select>
    </div>

    <p v-if="txns.error" class="text-sm text-red-600">{{ txns.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('finance.txnCol') }}</th>
            <th class="px-4 py-3">{{ $t('finance.typeCol') }}</th>
            <th class="px-4 py-3">{{ $t('finance.refCol') }}</th>
            <th class="px-4 py-3">{{ $t('finance.statusCol') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('finance.amountCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="txns.loading && !rows.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!rows.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('finance.noneMatch') }}</td>
          </tr>
          <tr v-for="t in rows" :key="t.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ t.name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ statusLabel(t.type) }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ t.ref || '—' }}</td>
            <td class="px-4 py-3"><StatusBadge :status="DOCSTATUS_LABEL[t.docstatus]" /></td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{{ formatMoney(t.amount_minor, t.currency) }}</td>
            <td class="px-4 py-3 text-right">
              <Button v-if="t.docstatus === 0" size="sm" variant="outline" @click="doSubmit(t.name)">{{ $t('finance.submitBtn') }}</Button>
              <Button v-else-if="t.docstatus === 1" size="sm" variant="outline" theme="red" @click="doCancel(t.name)">
                {{ $t('finance.cancelActionBtn') }}
              </Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
      <span>{{ txns.data?.total_count ?? 0 }} {{ $t('finance.countSuffix') }}</span>
      <div class="flex gap-2">
        <Button variant="outline" :disabled="page <= 1" @click="page -= 1">{{ $t('finance.previous') }}</Button>
        <Button variant="outline" :disabled="!hasNextPage" @click="page += 1">{{ $t('finance.next') }}</Button>
      </div>
    </div>

    <Dialog v-model="newTxnOpen" :options="{ title: $t('finance.newTxnDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('finance.typeField')">
            <select v-model="form.type" class="select-field w-full">
              <option v-for="t in TYPES" :key="t" :value="t">{{ statusLabel(t) }}</option>
            </select>
          </Field>
          <Field :label="$t('finance.amountField')">
            <input v-model.number="form.amount_minor" type="number" min="0" class="input-field" />
          </Field>
          <Field :label="$t('finance.currencyField')">
            <input v-model="form.currency" type="text" placeholder="USD" class="input-field" />
          </Field>
          <Field :label="$t('finance.referenceOptionalField')">
            <input v-model="form.ref" type="text" placeholder="e.g. RES-00001" class="input-field" />
          </Field>
        </div>
        <p v-if="createTxn.error" class="mt-3 text-sm text-red-600">{{ createTxn.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newTxnOpen = false">{{ $t('common.cancel') }}</Button>
          <Button
            variant="solid"
            :disabled="!form.amount_minor || !form.currency"
            :loading="createTxn.loading"
            @click="submitNewTxn"
          >
            {{ $t('finance.createDraft') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { cancelTxnResource, createTxnResource, financeSummaryResource, submitTxnResource, txnsResource } from '@/api/finance'
import { formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import KpiCard from '@/components/KpiCard.vue'
import Field from '@/components/Field.vue'

const TYPES = ['revenue', 'refund', 'tax', 'expense', 'payment']
const DOCSTATUS_LABEL = { 0: 'pending', 1: 'confirmed', 2: 'cancelled' }
const PAGE_LENGTH = 20

const typeFilter = ref('')
const page = ref(1)
const txns = txnsResource()
const summary = financeSummaryResource()
const createTxn = createTxnResource()
const submitTxnRes = submitTxnResource()
const cancelTxnRes = cancelTxnResource()

const rows = computed(() => txns.data?.data || [])
const hasNextPage = computed(() => rows.value.length === PAGE_LENGTH)

const newTxnOpen = ref(false)
const form = reactive({ type: 'revenue', amount_minor: null, currency: 'USD', ref: '' })

function load() {
  txns.fetch({ type: typeFilter.value || undefined, page: page.value, page_length: PAGE_LENGTH })
}
function loadSummary() {
  summary.fetch({})
}

onMounted(() => {
  load()
  loadSummary()
})
watch(page, load)
watch(typeFilter, () => {
  page.value = 1
  load()
})

function openNewTxn() {
  Object.assign(form, { type: 'revenue', amount_minor: null, currency: 'USD', ref: '' })
  createTxn.error = null
  newTxnOpen.value = true
}

function submitNewTxn() {
  createTxn.submit(
    { type: form.type, amount_minor: form.amount_minor, currency: form.currency, ref: form.ref || undefined },
    {
      onSuccess() {
        newTxnOpen.value = false
        load()
      },
    },
  )
}

function doSubmit(name) {
  submitTxnRes.submit({ name }, { onSuccess: () => { load(); loadSummary() } })
}
function doCancel(name) {
  cancelTxnRes.submit({ name }, { onSuccess: () => { load(); loadSummary() } })
}
</script>
