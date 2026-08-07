import { createApp } from 'vue'
import { frappeRequest, resourcesPlugin, setConfig } from 'frappe-ui'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './index.css'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)

app.use(router)
app.use(resourcesPlugin)
app.use(i18n)

document.documentElement.setAttribute('lang', i18n.global.locale.value)

app.mount('#app')
