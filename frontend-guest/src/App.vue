<template>
  <div v-if="closed" class="flex h-full min-h-screen flex-col items-center justify-center bg-gray-50 px-6 text-center">
    <div class="text-4xl">🏨</div>
    <h1 class="mt-4 text-xl font-semibold text-gray-900">{{ $t('closed.title') }}</h1>
    <p class="mt-2 max-w-md text-sm text-gray-600">{{ closedMessage }}</p>
    <LangSwitcher class="mt-6" />
  </div>
  <div v-else class="flex min-h-screen flex-col bg-white">
    <SiteHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import SiteHeader from '@/components/SiteHeader.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import LangSwitcher from '@/components/LangSwitcher.vue'
import { portalSettingsResource } from '@/api/booking'
import { portalSettings } from '@/store'

const { t } = useI18n()

// window.portal_enabled / window.closed_message come from www/book.py's
// boot context — first paint before get_portal_settings resolves uses
// these so a disabled portal never flashes the booking UI even for an
// instant. The default closed message is translated client-side (the
// Desk-configured Booking Portal Settings message, when set, always wins
// and is shown verbatim in whatever language the admin wrote it in).
const closed = ref(window.portal_enabled === false)
const closedMessage = ref(window.closed_message || t('closed.defaultMessage'))

const settings = portalSettingsResource()

onMounted(async () => {
  await settings.fetch()
  if (settings.data) {
    portalSettings.value = settings.data
    closed.value = !settings.data.enabled
    if (settings.data.closed_message) closedMessage.value = settings.data.closed_message
  }
})
</script>
