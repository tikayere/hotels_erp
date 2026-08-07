<template>
  <div>
    <!-- Hero -->
    <section class="relative overflow-hidden bg-gray-900 text-white">
      <div class="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <p v-if="property?.star_rating" class="text-sm tracking-wide text-gray-300">
          {{ '★'.repeat(property.star_rating) }}{{ '☆'.repeat(5 - property.star_rating) }}
        </p>
        <h1 class="mt-2 max-w-2xl text-3xl font-bold sm:text-5xl">
          {{ property?.property_name || $t('common.welcome') }}
        </h1>
        <p class="mt-4 max-w-xl text-lg text-gray-300">
          {{ property?.tagline || $t('home.defaultTagline') }}
        </p>
        <RouterLink :to="{ name: 'Book' }" class="btn-primary mt-8 !bg-white !text-gray-900 hover:!bg-gray-100">
          {{ $t('home.checkAvailability') }}
        </RouterLink>
      </div>
    </section>

    <!-- About -->
    <section v-if="property?.description" class="mx-auto max-w-3xl px-4 py-14 text-center sm:px-6">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">{{ $t('home.aboutUs') }}</h2>
      <div class="prose prose-sm mx-auto mt-3 text-gray-700" v-html="property.description"></div>
    </section>

    <!-- Rooms preview -->
    <section class="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <div class="mb-6 flex items-end justify-between">
        <h2 class="text-xl font-semibold text-gray-900">{{ $t('home.ourRooms') }}</h2>
        <RouterLink :to="{ name: 'Rooms' }" class="text-sm font-medium text-gray-600 hover:text-gray-900">
          {{ $t('home.viewAllRooms') }}
        </RouterLink>
      </div>

      <p v-if="rooms.error" class="text-sm text-red-600">{{ $t('home.loadRoomsError') }}</p>
      <div v-if="rooms.loading && !rooms.data" class="text-sm text-gray-500">{{ $t('home.loadingRooms') }}</div>

      <div v-else-if="rooms.data?.length" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <RoomCard v-for="room in rooms.data.slice(0, 3)" :key="room.room_type_code" :room="room" />
      </div>
      <p v-else-if="rooms.data" class="text-sm text-gray-500">{{ $t('home.noRoomsPublished') }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import RoomCard from '@/components/RoomCard.vue'
import { roomTypesResource } from '@/api/booking'
import { portalSettings } from '@/store'

const property = computed(() => portalSettings.value?.property)
const rooms = roomTypesResource()

onMounted(() => rooms.fetch())
</script>
