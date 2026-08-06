<template>
  <label class="block">
    <span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{{ label }}</span>
    <slot />
  </label>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
})
</script>
