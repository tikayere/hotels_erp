<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('rooms.title') }}</h1>
      <select
        v-model="statusFilter"
        class="rounded-md border-gray-200 bg-white py-1.5 text-sm text-gray-700 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
      >
        <option value="">{{ $t('rooms.allStatuses') }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
    </div>

    <p v-if="hierarchy.error" class="text-sm text-red-600">{{ hierarchy.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div v-if="hierarchy.loading && !hierarchy.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>
    <div v-else-if="!totalRooms" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('rooms.noneMatch') }}</div>

    <!-- Building -> Floor -> Room Type -> Room, so the physical layout is
         visible at a glance instead of one flat undifferentiated grid. -->
    <div v-else class="space-y-6">
      <section v-for="prop in hierarchy.data" :key="prop.property" class="space-y-3">
        <div class="flex items-center gap-3 rounded-lg border border-gray-100 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <img v-if="prop.logo" :src="prop.logo" class="size-10 rounded-md object-cover" :alt="prop.property_name" />
          <div v-else class="flex size-10 shrink-0 items-center justify-center rounded-md bg-gray-100 text-lg dark:bg-gray-800">🏢</div>
          <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">{{ prop.property_name }}</div>
            <div class="truncate text-xs text-gray-500 dark:text-gray-400">{{ [prop.city, prop.country].filter(Boolean).join(', ') || '—' }}</div>
          </div>
          <div class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{{ $t('rooms.roomCount', { n: prop.room_count }) }}</div>
        </div>

        <p v-if="!prop.floors.length" class="pl-2 text-sm text-gray-500 dark:text-gray-400">{{ $t('rooms.noneMatch') }}</p>

        <div
          v-for="floor in prop.floors"
          :key="floorKey(prop, floor)"
          class="ml-2 space-y-2 border-l-2 border-gray-100 pl-4 dark:border-gray-800"
        >
          <button
            type="button"
            class="flex items-center gap-2 py-1 text-left"
            @click="toggleFloor(floorKey(prop, floor))"
          >
            <span
              class="text-xs text-gray-400 transition-transform dark:text-gray-500"
              :class="isCollapsed(floorKey(prop, floor)) ? '-rotate-90' : ''"
            >▾</span>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ floor.floor ? `${$t('rooms.floor')} ${floor.floor}` : $t('rooms.unassignedFloor') }}
            </span>
            <span class="text-xs text-gray-400 dark:text-gray-500">{{ $t('rooms.roomCount', { n: floor.room_count }) }}</span>
          </button>

          <div v-if="!isCollapsed(floorKey(prop, floor))" class="space-y-2">
            <div
              v-for="rt in floor.room_types"
              :key="rt.room_type"
              class="flex flex-col gap-3 rounded-lg border border-gray-100 bg-white p-3 sm:flex-row dark:border-gray-800 dark:bg-gray-900"
            >
              <button type="button" class="shrink-0" @click="openGallery(rt)">
                <img v-if="rt.cover_image" :src="rt.cover_image" class="size-20 rounded-md object-cover" :alt="rt.room_type_name" />
                <div v-else class="flex size-20 items-center justify-center rounded-md bg-gray-100 text-2xl dark:bg-gray-800">🛏️</div>
              </button>

              <div class="min-w-0 flex-1 space-y-2">
                <div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <div>
                    <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ rt.room_type_name }}</span>
                    <span class="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{{ rt.code }}</span>
                  </div>
                  <button
                    type="button"
                    class="text-xs text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
                    @click="openGallery(rt)"
                  >
                    {{ rt.photos.length ? $t('rooms.viewPhotos', { n: rt.photos.length }) : $t('rooms.noPhotos') }}
                  </button>
                </div>
                <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
                  <span v-if="rt.bed_config">🛏️ {{ rt.bed_config }}</span>
                  <span>👤 {{ rt.max_occupancy_adults }}<template v-if="rt.max_occupancy_children">+{{ rt.max_occupancy_children }}</template></span>
                  <span v-if="rt.size_sqm">📐 {{ rt.size_sqm }} {{ $t('rooms.sqm') }}</span>
                </div>

                <div class="flex flex-wrap gap-1.5">
                  <RouterLink
                    v-for="r in rt.rooms"
                    :key="r.name"
                    :to="r.reservation ? { name: 'ReservationDetail', params: { id: r.reservation } } : {}"
                    class="flex items-center gap-1.5 rounded-md border border-gray-100 px-2 py-1 text-xs dark:border-gray-800"
                    :class="r.reservation ? 'transition hover:border-gray-300 dark:hover:border-gray-700' : ''"
                    :title="r.guest_name ? `${r.guest_name} · ${$t('rooms.checkOutPrefix')} ${formatDate(r.check_out)}` : ''"
                  >
                    <span class="size-1.5 rounded-full" :class="ROOM_STATUS_DOT[r.status] || 'bg-gray-400'" />
                    <span class="font-medium text-gray-900 dark:text-gray-100">{{ r.room_number }}</span>
                  </RouterLink>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <Dialog v-model="galleryOpen" :options="{ title: galleryRoomType?.room_type_name || '', size: '2xl' }">
      <template #body-content>
        <div v-if="galleryRoomType?.photos?.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <figure
            v-for="(p, i) in galleryRoomType.photos"
            :key="i"
            class="overflow-hidden rounded-lg border border-gray-100 dark:border-gray-800"
          >
            <img :src="p.image" :alt="p.caption || galleryRoomType.room_type_name" class="h-32 w-full object-cover" />
            <figcaption v-if="p.caption" class="truncate px-2 py-1 text-xs text-gray-500 dark:text-gray-400">{{ p.caption }}</figcaption>
          </figure>
        </div>
        <p v-else class="text-sm text-gray-500 dark:text-gray-400">{{ $t('rooms.noPhotos') }}</p>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Dialog } from 'frappe-ui'
import { roomHierarchyResource } from '@/api/pms'
import { activeProperty } from '@/property'
import { formatDate, statusLabel } from '@/utils/format'

const STATUSES = ['available', 'occupied', 'dirty', 'clean', 'maintenance', 'out_of_order']

// Mirrors StatusBadge.vue's color grouping (green=ready, blue=active,
// amber=needs attention, red=blocked) but as a plain dot rather than a full
// pill -- room chips here are small and repeated dozens of times per floor,
// so a text pill per room would be too noisy.
const ROOM_STATUS_DOT = {
  available: 'bg-green-500',
  clean: 'bg-green-500',
  occupied: 'bg-blue-500',
  dirty: 'bg-amber-500',
  maintenance: 'bg-amber-500',
  out_of_order: 'bg-red-500',
}

const statusFilter = ref('')
const hierarchy = roomHierarchyResource()

const totalRooms = computed(() => (hierarchy.data || []).reduce((sum, p) => sum + p.room_count, 0))

function load() {
  hierarchy.fetch({
    property: activeProperty.value || undefined,
    status: statusFilter.value || undefined,
  })
}

onMounted(load)
watch([activeProperty, statusFilter], load)

// Floors default expanded; collapsed state keyed "property::floor" so two
// properties' own "Floor 1" don't share collapse state.
const collapsedFloors = reactive(new Set())
function floorKey(prop, floor) {
  return `${prop.property}::${floor.floor ?? ''}`
}
function isCollapsed(key) {
  return collapsedFloors.has(key)
}
function toggleFloor(key) {
  if (collapsedFloors.has(key)) collapsedFloors.delete(key)
  else collapsedFloors.add(key)
}

const galleryOpen = ref(false)
const galleryRoomType = ref(null)
function openGallery(rt) {
  galleryRoomType.value = rt
  galleryOpen.value = true
}
</script>
