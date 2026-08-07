<template>
  <button
    type="button"
    class="rounded-md px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
    :aria-label="`${$t('lang.switchTo')}`"
    @click="toggle"
  >
    {{ locale === 'fr' ? '🇬🇧 EN' : '🇫🇷 FR' }}
  </button>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { setStoredLocale } from '@/i18n'

const { locale } = useI18n()

function toggle() {
  locale.value = locale.value === 'fr' ? 'en' : 'fr'
  setStoredLocale(locale.value)
  document.documentElement.setAttribute('lang', locale.value)
}
</script>
