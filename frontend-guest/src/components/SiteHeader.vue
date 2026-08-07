<template>
  <header class="sticky top-0 z-10 border-b border-gray-100 bg-white/90 backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
      <RouterLink :to="{ name: 'Home' }" class="flex items-center gap-2">
        <img v-if="property?.logo" :src="property.logo" alt="" class="h-9 w-9 rounded object-cover" />
        <span v-else class="text-2xl">🏨</span>
        <span class="text-base font-semibold text-gray-900">{{ property?.property_name || $t('common.hotelFallback') }}</span>
      </RouterLink>

      <nav class="hidden items-center gap-6 text-sm font-medium text-gray-600 sm:flex">
        <RouterLink :to="{ name: 'Home' }" class="hover:text-gray-900" active-class="text-gray-900">{{ $t('header.home') }}</RouterLink>
        <RouterLink :to="{ name: 'Rooms' }" class="hover:text-gray-900" active-class="text-gray-900">{{ $t('header.rooms') }}</RouterLink>
        <RouterLink :to="{ name: 'Lookup' }" class="hover:text-gray-900" active-class="text-gray-900">
          {{ $t('header.myBooking') }}
        </RouterLink>
      </nav>

      <div class="flex items-center gap-3">
        <LangSwitcher />
        <RouterLink :to="{ name: 'Book' }" class="btn-primary">{{ $t('header.bookNow') }}</RouterLink>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { portalSettings } from '@/store'
import LangSwitcher from '@/components/LangSwitcher.vue'

const property = computed(() => portalSettings.value?.property)
</script>
