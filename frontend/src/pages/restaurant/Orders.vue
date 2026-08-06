<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Restaurant</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">All statuses</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <Button variant="solid" @click="$router.push({ name: 'NewRestaurantOrder' })">+ New Order</Button>
      </div>
    </div>

    <p v-if="orders.error" class="text-sm text-red-600">{{ orders.error.messages?.[0] || 'Failed to load' }}</p>
    <div v-if="orders.loading && !orders.data" class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    <div v-else-if="!orders.data?.length" class="text-sm text-gray-500 dark:text-gray-400">No orders match these filters.</div>

    <div v-else class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">Order</th>
            <th class="px-4 py-3">Reservation</th>
            <th class="px-4 py-3">Assigned To</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3 text-right">Amount</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr
            v-for="o in orders.data"
            :key="o.name"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60"
            @click="$router.push({ name: 'RestaurantOrderDetail', params: { id: o.name } })"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ o.name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ o.reservation || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ o.assigned_to || '—' }}</td>
            <td class="px-4 py-3"><StatusBadge :status="o.status" /></td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
              {{ formatMoney(o.amount_minor, o.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { ordersResource } from '@/api/restaurant'
import { formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'

const STATUSES = ['placed', 'in_kitchen', 'served', 'billed', 'cancelled']

const statusFilter = ref('')
const orders = ordersResource()

function load() {
  orders.fetch({ status: statusFilter.value || undefined })
}

onMounted(load)
watch(statusFilter, load)
</script>
