<!-- The `rounded-lg border ... bg-white p-5 ... dark:bg-gray-900` box every
     page already repeats inline (see ReservationDetail.vue) — pulled out
     once the module pages below made that four-line class list common
     enough to be worth naming, not changed on the pages that predate it. -->
<template>
  <div class="rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
    <div v-if="title" class="mb-4 flex items-center justify-between">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ title }}</h2>
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>
