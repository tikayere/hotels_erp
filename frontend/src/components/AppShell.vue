<template>
  <div class="flex h-full min-h-screen bg-gray-50 dark:bg-gray-950">
    <!-- Sidebar -->
    <aside
      class="flex w-60 shrink-0 flex-col border-r border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900"
    >
      <div class="flex items-center gap-2 px-5 py-4">
        <span class="text-xl">🛎️</span>
        <span class="font-semibold text-gray-900 dark:text-gray-100">Front Desk</span>
      </div>

      <nav class="flex flex-1 flex-col gap-4 overflow-y-auto px-3 pb-3">
        <div v-for="(section, i) in visibleSections" :key="i" class="flex flex-col gap-1">
          <div v-if="section.label" class="px-3 pt-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
            {{ section.label }}
          </div>
          <RouterLink
            v-for="item in section.items"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            active-class="!bg-gray-900 !text-white dark:!bg-gray-100 dark:!text-gray-900"
            exact-active-class="!bg-gray-900 !text-white dark:!bg-gray-100 dark:!text-gray-900"
          >
            <span>{{ item.icon }}</span>
            {{ item.label }}
          </RouterLink>
        </div>
      </nav>

      <div class="border-t border-gray-100 p-3 dark:border-gray-800">
        <Button variant="solid" class="w-full" @click="$router.push({ name: 'NewReservation' })">
          + New Reservation
        </Button>
      </div>

      <div class="flex items-center justify-between gap-2 border-t border-gray-100 p-3 dark:border-gray-800">
        <div class="min-w-0">
          <div class="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
            {{ boot.data?.full_name || user }}
          </div>
          <div class="truncate text-xs text-gray-500 dark:text-gray-400">
            {{ (boot.data?.roles || []).join(', ') || '…' }}
          </div>
        </div>
        <button
          class="rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
          @click="logout"
        >
          Log out
        </button>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header
        class="flex items-center justify-between gap-4 border-b border-gray-100 bg-white px-6 py-3 dark:border-gray-800 dark:bg-gray-900"
      >
        <div class="flex items-center gap-2">
          <label class="text-xs font-medium text-gray-500 dark:text-gray-400" for="property-select">
            Property
          </label>
          <select
            id="property-select"
            v-model="activeProperty"
            class="rounded-md border-gray-200 bg-white py-1.5 text-sm text-gray-700 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
          >
            <option value="">All properties</option>
            <option v-for="p in boot.data?.properties || []" :key="p.name" :value="p.name">
              {{ p.property_name }}
            </option>
          </select>
        </div>
        <slot name="header-actions" />
      </header>

      <main class="flex-1 overflow-y-auto p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import { boot, logout, user } from '@/session'
import { activeProperty } from '@/property'

// Every staff role sees Front Desk; everything below it is gated by
// `boot.data.modules` — the same module-key -> role-tuple mapping
// `hotel_erp.api.pms.get_boot_info` computes server-side (see
// `_MODULE_ROLES` there), kept in sync by naming convention (`module` here
// must match a key in that dict) rather than duplicating the role tuples
// themselves into the frontend too.
const NAV_SECTIONS = [
  {
    label: '',
    module: null,
    items: [
      { to: '/', label: 'Dashboard', icon: '📊' },
      { to: '/rooms', label: 'Rooms', icon: '🚪' },
      { to: '/reservations', label: 'Reservations', icon: '📖' },
    ],
  },
  {
    label: 'Operations',
    module: 'housekeeping',
    items: [{ to: '/housekeeping', label: 'Housekeeping', icon: '🧹' }],
  },
  {
    label: 'Operations',
    module: 'maintenance',
    items: [{ to: '/maintenance', label: 'Maintenance', icon: '🛠️' }],
  },
  {
    label: 'Operations',
    module: 'restaurant',
    items: [{ to: '/restaurant', label: 'Restaurant', icon: '🍽️' }],
  },
  {
    label: 'Operations',
    module: 'conference',
    items: [{ to: '/conference', label: 'Conference & Events', icon: '🗓️' }],
  },
  {
    label: 'Guests',
    module: 'crm',
    items: [
      { to: '/guests', label: 'Guest Directory', icon: '🧑‍🤝‍🧑' },
      { to: '/complaints', label: 'Complaints', icon: '⚠️' },
    ],
  },
  {
    label: 'Back Office',
    module: 'finance',
    items: [{ to: '/finance', label: 'Finance', icon: '💰' }],
  },
  {
    label: 'Back Office',
    module: 'hr',
    items: [
      { to: '/hr/staff', label: 'Staff', icon: '🧑‍💼' },
      { to: '/hr/leave', label: 'Leave', icon: '🌴' },
      { to: '/hr/payroll', label: 'Payroll', icon: '🧾' },
    ],
  },
  {
    label: 'Back Office',
    module: 'inventory',
    items: [
      { to: '/inventory', label: 'Inventory', icon: '📦' },
      { to: '/inventory/suppliers', label: 'Suppliers', icon: '🚚' },
      { to: '/inventory/purchase-orders', label: 'Purchase Orders', icon: '🧮' },
    ],
  },
]

const visibleSections = computed(() => {
  const modules = boot.data?.modules || []
  // Collapse consecutive same-label sections (e.g. the four "Operations"
  // entries above) into one group with one header, once role-gating has
  // trimmed the list down -- kept as separate entries above so each
  // module's gate stays a one-line, easy-to-scan `module:` key.
  const visible = NAV_SECTIONS.filter((s) => !s.module || modules.includes(s.module))
  const merged = []
  for (const section of visible) {
    const last = merged[merged.length - 1]
    if (last && last.label === section.label) {
      last.items.push(...section.items)
    } else {
      merged.push({ label: section.label, items: [...section.items] })
    }
  }
  return merged
})
</script>
