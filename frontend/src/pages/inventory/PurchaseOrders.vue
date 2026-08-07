<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('purchaseOrders.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">{{ $t('common.allStatuses') }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <Button v-if="canWrite" variant="solid" @click="openNew">{{ $t('purchaseOrders.newPO') }}</Button>
      </div>
    </div>

    <p v-if="orders.error" class="text-sm text-red-600">{{ orders.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('purchaseOrders.poCol') }}</th>
            <th class="px-4 py-3">{{ $t('purchaseOrders.supplierCol') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('purchaseOrders.totalCol') }}</th>
            <th class="px-4 py-3">{{ $t('purchaseOrders.statusCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="orders.loading && !orders.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!orders.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('purchaseOrders.noneMatch') }}</td>
          </tr>
          <tr v-for="o in orders.data" :key="o.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ o.name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ o.supplier }}</td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{{ formatMoney(o.total_amount_minor, o.currency) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="o.status" /></td>
            <td class="px-4 py-3 text-right">
              <div v-if="canWrite" class="flex justify-end gap-2">
                <Button v-if="o.status === 'draft'" size="sm" variant="outline" @click="doAction(markOrdered, o.name)">
                  {{ $t('purchaseOrders.markOrderedBtn') }}
                </Button>
                <Button v-if="o.status === 'ordered'" size="sm" variant="outline" theme="green" @click="doAction(markReceived, o.name)">
                  {{ $t('purchaseOrders.markReceivedBtn') }}
                </Button>
                <Button
                  v-if="!['received', 'cancelled'].includes(o.status)"
                  size="sm"
                  variant="outline"
                  theme="red"
                  @click="doAction(cancelPO, o.name)"
                >
                  {{ $t('common.cancel') }}
                </Button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="newOpen" :options="{ title: $t('purchaseOrders.newDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('purchaseOrders.supplierField')">
            <input v-model="form.supplier" type="text" :placeholder="$t('purchaseOrders.supplierPlaceholder')" class="input-field" />
          </Field>
          <Field :label="$t('purchaseOrders.currencyField')">
            <input v-model="form.currency" type="text" placeholder="USD" class="input-field" />
          </Field>
        </div>
        <div class="mt-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ $t('purchaseOrders.lineItemsLabel') }}</span>
            <Button size="sm" variant="outline" @click="addLine">{{ $t('purchaseOrders.addLine') }}</Button>
          </div>
          <div v-for="(line, i) in lines" :key="i" class="grid grid-cols-12 items-center gap-2">
            <input v-model="line.item" type="text" :placeholder="$t('purchaseOrders.itemNamePlaceholder')" class="input-field col-span-6" />
            <input v-model.number="line.qty" type="number" min="1" :placeholder="$t('purchaseOrders.qtyPlaceholder')" class="input-field col-span-2" />
            <input v-model.number="line.price_minor" type="number" min="0" :placeholder="$t('purchaseOrders.pricePlaceholder')" class="input-field col-span-3" />
            <button type="button" class="col-span-1 text-gray-400 hover:text-red-600" @click="lines.splice(i, 1)">✕</button>
          </div>
        </div>
        <div class="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 text-sm dark:border-gray-800">
          <span class="text-gray-500 dark:text-gray-400">{{ $t('purchaseOrders.totalLabel') }}</span>
          <span class="font-semibold text-gray-900 dark:text-gray-100">{{ formatMoney(totalMinor, form.currency) }}</span>
        </div>
        <p v-if="createPO.error" class="mt-3 text-sm text-red-600">{{ createPO.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!canSubmit" :loading="createPO.loading" @click="submit">{{ $t('purchaseOrders.createBtn') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import {
  cancelPurchaseOrderResource,
  createPurchaseOrderResource,
  markOrderedResource,
  markReceivedResource,
  purchaseOrdersResource,
} from '@/api/inventory'
import { boot } from '@/session'
import { formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['draft', 'ordered', 'received', 'cancelled']

const statusFilter = ref('')
const orders = purchaseOrdersResource()
const createPO = createPurchaseOrderResource()
const markOrdered = markOrderedResource()
const markReceived = markReceivedResource()
const cancelPO = cancelPurchaseOrderResource()
const canWrite = computed(() => (boot.data?.roles || []).includes('System Manager'))

function load() {
  orders.fetch({ status: statusFilter.value || undefined })
}
onMounted(load)
watch(statusFilter, load)

function doAction(resource, name) {
  resource.submit({ name }, { onSuccess: load })
}

const newOpen = ref(false)
const form = reactive({ supplier: '', currency: 'USD' })
const lines = reactive([{ item: '', qty: 1, price_minor: 0 }])

const totalMinor = computed(() =>
  lines.reduce((sum, l) => sum + (Number(l.qty) || 0) * (Number(l.price_minor) || 0), 0),
)
const canSubmit = computed(
  () => form.supplier && form.currency && lines.some((l) => l.item && Number(l.qty) > 0) && totalMinor.value > 0,
)

function addLine() {
  lines.push({ item: '', qty: 1, price_minor: 0 })
}
function openNew() {
  Object.assign(form, { supplier: '', currency: 'USD' })
  lines.splice(0, lines.length, { item: '', qty: 1, price_minor: 0 })
  createPO.error = null
  newOpen.value = true
}
function submit() {
  const items = lines.filter((l) => l.item && Number(l.qty) > 0)
  createPO.submit(
    { supplier: form.supplier, items: JSON.stringify(items), total_amount_minor: totalMinor.value, currency: form.currency },
    { onSuccess: () => { newOpen.value = false; load() } },
  )
}
</script>
