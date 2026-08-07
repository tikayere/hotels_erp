<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('reservations.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="search"
          type="search"
          :placeholder="$t('reservations.searchPlaceholder')"
          class="w-56 rounded-md border-gray-200 bg-white py-1.5 text-sm text-gray-700 placeholder:text-gray-400 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
        />
        <select
          v-model="statusFilter"
          class="rounded-md border-gray-200 bg-white py-1.5 text-sm text-gray-700 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">{{ $t('common.allStatuses') }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
      </div>
    </div>

    <p v-if="reservations.error" class="text-sm text-red-600">
      {{ reservations.error.messages?.[0] || $t('common.failedToLoad') }}
    </p>

    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('reservations.confirmationNumber') }}</th>
            <th class="px-4 py-3">{{ $t('reservations.guest') }}</th>
            <th class="px-4 py-3">{{ $t('reservations.roomType') }}</th>
            <th class="px-4 py-3">{{ $t('reservations.stay') }}</th>
            <th class="px-4 py-3">{{ $t('reservations.status') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('reservations.total') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="reservations.loading && !rows.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!rows.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('reservations.noneMatch') }}</td>
          </tr>
          <tr
            v-for="r in rows"
            :key="r.name"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60"
            @click="$router.push({ name: 'ReservationDetail', params: { id: r.name } })"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ r.confirmation_number }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ r.guest_name || '—' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ r.room_type_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">
              {{ formatDate(r.check_in) }} → {{ formatDate(r.check_out) }}
            </td>
            <td class="px-4 py-3"><StatusBadge :status="r.status" /></td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
              {{ formatMoney(r.total_amount_minor, r.currency) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
      <span>{{ reservations.data?.total_count ?? 0 }} {{ $t('reservations.countSuffix') }}</span>
      <div class="flex gap-2">
        <Button variant="outline" :disabled="page <= 1" @click="page -= 1">{{ $t('reservations.previous') }}</Button>
        <Button variant="outline" :disabled="!hasNextPage" @click="page += 1">{{ $t('reservations.next') }}</Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { useRoute } from 'vue-router'
import { reservationsResource } from '@/api/pms'
import { activeProperty } from '@/property'
import { formatDate, formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'

const STATUSES = ['confirmed', 'checked_in', 'checked_out', 'cancelled', 'no_show']
const PAGE_LENGTH = 20

const route = useRoute()
const search = ref('')
const statusFilter = ref(route.query.status || '')
const arrivalsOn = ref(route.query.arrivals_on || '')
const page = ref(1)

const reservations = reservationsResource()
const rows = computed(() => reservations.data?.data || [])
const hasNextPage = computed(() => rows.value.length === PAGE_LENGTH)

let searchDebounce
function load() {
  reservations.fetch({
    status: statusFilter.value || undefined,
    search: search.value || undefined,
    arrivals_on: arrivalsOn.value || undefined,
    property: activeProperty.value || undefined,
    page: page.value,
    page_length: PAGE_LENGTH,
  })
}

onMounted(load)
watch(page, load)
watch([statusFilter, activeProperty, arrivalsOn], () => {
  page.value = 1
  load()
})
watch(search, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})
</script>
