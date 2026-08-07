<template>
  <div class="mx-auto max-w-6xl px-4 py-12 sm:px-6">
    <h1 class="text-2xl font-semibold text-gray-900">{{ $t('rooms.title') }}</h1>
    <p class="mt-1 text-sm text-gray-600">{{ $t('rooms.subtitle') }}</p>

    <p v-if="rooms.error" class="mt-6 text-sm text-red-600">{{ $t('rooms.loadError') }}</p>
    <div v-if="rooms.loading && !rooms.data" class="mt-6 text-sm text-gray-500">{{ $t('rooms.loading') }}</div>

    <div v-else-if="rooms.data?.length" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <RoomCard v-for="room in rooms.data" :key="room.room_type_code" :room="room" />
    </div>
    <p v-else-if="rooms.data" class="mt-6 text-sm text-gray-500">{{ $t('rooms.noneYet') }}</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import RoomCard from '@/components/RoomCard.vue'
import { roomTypesResource } from '@/api/booking'

const rooms = roomTypesResource()
onMounted(() => rooms.fetch())
</script>
