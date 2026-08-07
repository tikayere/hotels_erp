<template>
  <div class="overflow-hidden rounded-lg border border-gray-100 bg-white shadow-sm transition hover:shadow-md">
    <div class="aspect-[4/3] w-full bg-gray-100">
      <img v-if="room.cover_image" :src="room.cover_image" :alt="room.name" class="h-full w-full object-cover" />
      <div v-else class="flex h-full w-full items-center justify-center text-4xl">🛏️</div>
    </div>
    <div class="p-4">
      <div class="flex items-start justify-between gap-2">
        <h3 class="text-base font-semibold text-gray-900">{{ room.name }}</h3>
        <div v-if="room.from_price_minor != null" class="shrink-0 text-right">
          <div class="text-xs text-gray-500">{{ $t('roomCard.from') }}</div>
          <div class="text-sm font-semibold text-gray-900">{{ formatMoney(room.from_price_minor, currency) }}</div>
        </div>
      </div>
      <p class="mt-1 line-clamp-2 text-sm text-gray-600" v-html="room.description"></p>
      <div class="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
        <span>👤 {{ $t('roomCard.upToAdults', { n: room.max_occupancy_adults }) }}</span>
        <span v-if="room.bed_config">🛏️ {{ room.bed_config }}</span>
        <span v-if="room.size_sqm">📐 {{ $t('roomCard.sizeSqm', { n: room.size_sqm }) }}</span>
      </div>
      <div v-if="room.amenities?.length" class="mt-2 flex flex-wrap gap-1">
        <span
          v-for="a in room.amenities.slice(0, 4)"
          :key="a"
          class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
        >
          {{ a }}
        </span>
        <span v-if="room.amenities.length > 4" class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          +{{ room.amenities.length - 4 }} {{ $t('roomCard.more') }}
        </span>
      </div>
      <RouterLink
        :to="{ name: 'Book', query: { room: room.room_type_code } }"
        class="btn-primary mt-4 w-full"
      >
        {{ $t('roomCard.bookThisRoom') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { formatMoney } from '@/store'

defineProps({
  room: { type: Object, required: true },
  currency: { type: String, default: '' },
})
</script>
