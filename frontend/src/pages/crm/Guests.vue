<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Guests</h1>
      <input v-model="search" type="search" placeholder="Search guest name…" class="input-field w-64" />
    </div>

    <p v-if="guests.error" class="text-sm text-red-600">{{ guests.error.messages?.[0] || 'Failed to load' }}</p>
    <div v-if="guests.loading && !guests.data" class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    <div v-else-if="!guests.data?.length" class="text-sm text-gray-500 dark:text-gray-400">No guests found.</div>

    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="g in guests.data"
        :key="g.name"
        :to="{ name: 'GuestDetail', params: { id: g.name } }"
        class="flex flex-col gap-1 rounded-lg border border-gray-100 bg-white p-4 transition hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ g.guest_name }}</span>
          <span v-if="g.vip_status" class="text-xs font-medium text-amber-600 dark:text-amber-400">★ VIP</span>
        </div>
        <div class="text-xs text-gray-500 dark:text-gray-400">{{ g.phone || g.email || 'No contact on file' }}</div>
        <div class="text-xs text-gray-400">{{ g.loyalty_points || 0 }} loyalty points</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { searchGuestsResource } from '@/api/crm'

const search = ref('')
const guests = searchGuestsResource()

let debounce
function load() {
  guests.fetch({ search: search.value || undefined })
}
onMounted(load)
watch(search, () => {
  clearTimeout(debounce)
  debounce = setTimeout(load, 300)
})
</script>
