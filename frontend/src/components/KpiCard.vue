<template>
  <RouterLink
    :to="to || {}"
    class="rounded-lg border border-gray-100 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
    :class="to ? 'transition hover:border-gray-300 dark:hover:border-gray-700' : 'pointer-events-none'"
  >
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ label }}</span>
      <span class="text-base leading-none">{{ icon }}</span>
    </div>
    <div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-100">{{ value ?? '—' }}</div>
  </RouterLink>
</template>

<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: null },
  icon: { type: String, default: '' },
  to: { type: [Object, String], default: null },
})
</script>
