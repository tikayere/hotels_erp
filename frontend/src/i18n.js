import { createI18n } from 'vue-i18n'
import fr from '@/locales/fr.json'
import en from '@/locales/en.json'

// French is the default for the whole staff app (Burkina Faso deployment),
// with English available as an explicit opt-in via LangSwitcher.vue in
// AppShell.vue. The choice is remembered per-browser so it survives a
// reload. `legacy: false` (Composition API mode) is required so plain JS
// modules like utils/format.js can read `i18n.global.t` directly, outside
// any component's setup().
const STORAGE_KEY = 'hotel_erp_pms_locale'

export function getStoredLocale() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'fr' || stored === 'en') return stored
  return 'fr'
}

export function setStoredLocale(locale) {
  localStorage.setItem(STORAGE_KEY, locale)
}

const i18n = createI18n({
  legacy: false,
  locale: getStoredLocale(),
  fallbackLocale: 'fr',
  messages: { fr, en },
})

export default i18n
