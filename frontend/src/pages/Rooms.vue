<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Rooms</h1>
      <select
        v-model="statusFilter"
        class="rounded-md border-gray-200 bg-white py-1.5 text-sm text-gray-700 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
      >
        <option value="">All statuses</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
    </div>

    <p v-if="rooms.error" class="text-sm text-red-600">{{ rooms.error.messages?.[0] || 'Failed to load' }}</p>
    <div v-if="rooms.loading && !rooms.data" class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    <div v-else-if="!rooms.data?.length" class="text-sm text-gray-500 dark:text-gray-400">No rooms match these filters.</div>

    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      <RouterLink
        v-for="r in rooms.data"
        :key="r.name"
        :to="r.reservation ? { name: 'ReservationDetail', params: { id: r.reservation } } : {}"
        class="flex flex-col gap-2 rounded-lg border border-gray-100 bg-white p-3 dark:border-gray-800 dark:bg-gray-900"
        :class="r.reservation ? 'transition hover:border-gray-300 dark:hover:border-gray-700' : ''"
      >
        <div class="flex items-start justify-between">
          <span class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ r.room_number }}</span>
          <StatusBadge :status="r.status" />
        </div>
        <div class="text-xs text-gray-500 dark:text-gray-400">{{ r.room_type_name }} · Floor {{ r.floor || '—' }}</div>
        <div v-if="r.guest_name" class="text-xs text-gray-700 dark:text-gray-300">
          {{ r.guest_name }} · out {{ formatDate(r.check_out) }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { roomsResource } from '@/api/pms'
import { activeProperty } from '@/property'
import { formatDate, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'

const STATUSES = ['available', 'occupied', 'dirty', 'clean', 'maintenance', 'out_of_order']

const statusFilter = ref('')
const rooms = roomsResource()

function load() {
  rooms.fetch({
    property: activeProperty.value || undefined,
    status: statusFilter.value || undefined,
  })
}

onMounted(load)
watch([activeProperty, statusFilter], load)
</script>
