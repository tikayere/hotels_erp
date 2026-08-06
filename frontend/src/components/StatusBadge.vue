<!-- Small colored pill for a Reservation/Room/Task status value. Color groups
     map by meaning (green = ready/good, blue = active, amber = needs
     attention, red = blocked/cancelled) rather than 1:1 per status, so new
     status values added later degrade to a sane default color instead of
     needing this file touched too. -->
<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
    :class="colorClasses"
  >
    <span class="size-1.5 rounded-full" :class="dotClasses" />
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { statusLabel } from '@/utils/format'

const props = defineProps({
  status: { type: String, required: true },
})

const GROUPS = {
  green: ['confirmed', 'available', 'clean', 'completed', 'verified', 'resolved', 'approved', 'received', 'paid', 'active'],
  blue: ['checked_in', 'occupied', 'in_progress', 'assigned', 'processed', 'ordered', 'placed', 'in_kitchen'],
  amber: ['dirty', 'pending', 'open', 'maintenance', 'no_show', 'tentative', 'high', 'medium', 'on_leave'],
  red: ['cancelled', 'out_of_order', 'closed', 'urgent', 'rejected', 'escalated', 'terminated'],
}

const group = computed(() => {
  for (const [name, statuses] of Object.entries(GROUPS)) {
    if (statuses.includes(props.status)) return name
  }
  return 'gray'
})

const label = computed(() => statusLabel(props.status))

const colorClasses = computed(
  () =>
    ({
      green: 'bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-400',
      blue: 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
      amber: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
      red: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
      gray: 'bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400',
    })[group.value],
)

const dotClasses = computed(
  () =>
    ({
      green: 'bg-green-500',
      blue: 'bg-blue-500',
      amber: 'bg-amber-500',
      red: 'bg-red-500',
      gray: 'bg-gray-400',
    })[group.value],
)
</script>
