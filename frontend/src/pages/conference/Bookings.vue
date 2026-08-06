<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Conference &amp; Events</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">All statuses</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <Button variant="solid" @click="$router.push({ name: 'NewConferenceBooking' })">+ New Booking</Button>
      </div>
    </div>

    <p v-if="bookings.error" class="text-sm text-red-600">{{ bookings.error.messages?.[0] || 'Failed to load' }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">Space</th>
            <th class="px-4 py-3">Booked By</th>
            <th class="px-4 py-3">When</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="bookings.loading && !bookings.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">Loading…</td>
          </tr>
          <tr v-else-if="!bookings.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">No bookings match these filters.</td>
          </tr>
          <tr v-for="b in bookings.data" :key="b.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ b.space_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ b.booked_by }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDateTime(b.start_at) }} → {{ formatDateTime(b.end_at) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="b.status" /></td>
            <td class="px-4 py-3 text-right">
              <div v-if="b.status !== 'cancelled'" class="flex justify-end gap-2">
                <Button v-if="b.status === 'tentative'" size="sm" variant="outline" theme="green" @click="doConfirm(b.name)">
                  Confirm
                </Button>
                <Button size="sm" variant="outline" theme="red" @click="doCancel(b.name)">Cancel</Button>
              </div>
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
import { bookingsResource, cancelBookingResource, confirmBookingResource } from '@/api/conference'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'

const STATUSES = ['tentative', 'confirmed', 'cancelled']

const statusFilter = ref('')
const bookings = bookingsResource()
const confirmBooking = confirmBookingResource()
const cancelBooking = cancelBookingResource()

function load() {
  bookings.fetch({ status: statusFilter.value || undefined })
}
onMounted(load)
watch(statusFilter, load)

function doConfirm(name) {
  confirmBooking.submit({ name }, { onSuccess: load })
}
function doCancel(name) {
  cancelBooking.submit({ name }, { onSuccess: load })
}
</script>
