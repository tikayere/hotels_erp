<template>
  <div>
    <div class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ label }}</div>
    <div class="text-sm text-gray-900 dark:text-gray-100">{{ value ?? '—' }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
})
</script>
