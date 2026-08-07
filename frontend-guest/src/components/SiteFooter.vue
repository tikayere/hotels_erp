<template>
  <footer class="border-t border-gray-100 bg-gray-50">
    <div class="mx-auto max-w-6xl px-4 py-8 text-sm text-gray-600 sm:px-6">
      <div class="flex flex-col gap-6 sm:flex-row sm:justify-between">
        <div>
          <div class="font-semibold text-gray-900">{{ property?.property_name || $t('common.hotelFallback') }}</div>
          <div v-if="addressLine" class="mt-1">{{ addressLine }}</div>
        </div>
        <div class="space-y-1">
          <div v-if="property?.phone">📞 {{ property.phone }}</div>
          <div v-if="property?.email">✉️ {{ property.email }}</div>
          <div v-if="property?.website">🌐 {{ property.website }}</div>
        </div>
      </div>
      <div class="mt-6 flex items-center justify-between border-t border-gray-200 pt-4 text-xs text-gray-400">
        <span>© {{ year }} {{ property?.property_name || $t('common.hotelFallback') }}. {{ $t('footer.rights') }}</span>
        <RouterLink :to="{ name: 'Lookup' }" class="hover:text-gray-600">{{ $t('footer.findBooking') }}</RouterLink>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { portalSettings } from '@/store'

const property = computed(() => portalSettings.value?.property)
const year = new Date().getFullYear()
const addressLine = computed(() => {
  const p = property.value
  if (!p) return ''
  return [p.address, p.city, p.country].filter(Boolean).join(', ')
})
</script>
