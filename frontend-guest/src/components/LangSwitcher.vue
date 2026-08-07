<template>
  <button
    type="button"
    class="rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:border-gray-400 hover:text-gray-900"
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
