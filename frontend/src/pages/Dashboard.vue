<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('dashboard.title') }}</h1>
      <span class="text-sm text-gray-500 dark:text-gray-400">{{ dashboard.data?.date }}</span>
    </div>

    <p v-if="dashboard.error" class="text-sm text-red-600">{{ dashboard.error.messages?.[0] || $t('common.failedToLoad') }}</p>

    <div v-if="dashboard.loading && !dashboard.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="dashboard.data">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard
          :label="$t('dashboard.arrivalsToday')"
          icon="🛬"
          :value="dashboard.data.arrivals_today"
          :to="{ name: 'Reservations', query: { status: 'confirmed', arrivals_on: dashboard.data.date } }"
        />
        <KpiCard
          :label="$t('dashboard.departuresToday')"
          icon="🛫"
          :value="dashboard.data.departures_today"
          :to="{ name: 'Reservations', query: { status: 'checked_in' } }"
        />
        <KpiCard
          :label="$t('dashboard.inHouse')"
          icon="🛏️"
          :value="dashboard.data.in_house"
          :to="{ name: 'Reservations', query: { status: 'checked_in' } }"
        />
        <KpiCard :label="$t('dashboard.housekeepingOpen')" icon="🧹" :value="dashboard.data.pending_housekeeping_tasks" />
        <KpiCard :label="$t('dashboard.maintenanceOpen')" icon="🛠️" :value="dashboard.data.open_maintenance_requests" />
      </div>

      <div class="rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ $t('dashboard.roomsByStatus') }}</h2>
          <RouterLink :to="{ name: 'Rooms' }" class="text-xs font-medium text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
            {{ $t('dashboard.viewRoomBoard') }}
          </RouterLink>
        </div>
        <div v-if="!Object.keys(dashboard.data.rooms_by_status).length" class="text-sm text-gray-500">
          {{ $t('dashboard.noRoomsFound') }}
        </div>
        <div v-else class="flex flex-wrap gap-3">
          <div
            v-for="(count, status) in dashboard.data.rooms_by_status"
            :key="status"
            class="flex items-center gap-2 rounded-md border border-gray-100 px-3 py-2 dark:border-gray-800"
          >
            <StatusBadge :status="status" />
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ count }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { dashboardResource } from '@/api/pms'
import { activeProperty } from '@/property'
import StatusBadge from '@/components/StatusBadge.vue'
import KpiCard from '@/components/KpiCard.vue'

const dashboard = dashboardResource()

function load() {
  dashboard.fetch({ property: activeProperty.value || undefined })
}

onMounted(load)
watch(activeProperty, load)
</script>
