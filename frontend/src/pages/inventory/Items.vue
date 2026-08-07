<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('inventory.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="categoryFilter" class="select-field">
          <option value="">{{ $t('inventory.allCategories') }}</option>
          <option v-for="c in CATEGORIES" :key="c" :value="c">{{ statusLabel(c) }}</option>
        </select>
        <label class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <input v-model="lowStockOnly" type="checkbox" class="rounded border-gray-300" />
          {{ $t('inventory.lowStockOnly') }}
        </label>
        <Button v-if="canWrite" variant="solid" @click="openNewItem">{{ $t('inventory.newItem') }}</Button>
      </div>
    </div>

    <p v-if="items.error" class="text-sm text-red-600">{{ items.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('inventory.itemCol') }}</th>
            <th class="px-4 py-3">{{ $t('inventory.categoryCol') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('inventory.onHandCol') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('inventory.reorderLevelCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="items.loading && !items.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!items.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('inventory.noneMatch') }}</td>
          </tr>
          <tr
            v-for="i in items.data"
            :key="i.name"
            :class="canWrite ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60' : ''"
            @click="canWrite && openEditItem(i)"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ i.item_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ statusLabel(i.category) }}</td>
            <td
              class="px-4 py-3 text-right"
              :class="isLow(i) ? 'font-semibold text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'"
            >
              {{ i.quantity_on_hand ?? 0 }} {{ i.unit || '' }}
            </td>
            <td class="px-4 py-3 text-right text-gray-500 dark:text-gray-400">{{ i.reorder_level ?? '—' }}</td>
            <td class="px-4 py-3 text-right">
              <span v-if="isLow(i)" class="text-xs font-medium text-red-600 dark:text-red-400">{{ $t('inventory.reorder') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="dialogOpen" :options="{ title: editing ? $t('inventory.editDialogTitle', { name: editing.item_name }) : $t('inventory.newDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field v-if="!editing" :label="$t('inventory.itemNameField')">
            <input v-model="form.item_name" type="text" class="input-field" />
          </Field>
          <Field v-if="!editing" :label="$t('inventory.categoryField')">
            <select v-model="form.category" class="select-field w-full">
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ statusLabel(c) }}</option>
            </select>
          </Field>
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('inventory.quantityOnHandField')">
              <input v-model.number="form.quantity_on_hand" type="number" min="0" class="input-field" />
            </Field>
            <Field :label="$t('inventory.reorderLevelField')">
              <input v-model.number="form.reorder_level" type="number" min="0" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('inventory.unitOptionalField')">
            <input v-model="form.unit" type="text" :placeholder="$t('inventory.unitPlaceholder')" class="input-field" />
          </Field>
        </div>
        <p v-if="actionError" class="mt-3 text-sm text-red-600">{{ actionError }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="dialogOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :loading="saving" @click="save">{{ editing ? $t('common.save') : $t('inventory.createItemBtn') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { createItemResource, itemsResource, updateItemResource } from '@/api/inventory'
import { boot } from '@/session'
import { statusLabel } from '@/utils/format'
import Field from '@/components/Field.vue'

const CATEGORIES = ['linen', 'cleaning_supplies', 'food', 'maintenance_supplies']

const categoryFilter = ref('')
const lowStockOnly = ref(false)
const items = itemsResource()
const createItem = createItemResource()
const updateItem = updateItemResource()

// Writes are System-Manager-only server-side (see api/inventory.py); hide
// the create/edit affordances for the read-only Housekeeping Staff tier
// rather than let them click into a form that will just 403.
const canWrite = computed(() => (boot.data?.roles || []).includes('System Manager'))

function load() {
  items.fetch({ category: categoryFilter.value || undefined, low_stock: lowStockOnly.value || undefined })
}
onMounted(load)
watch([categoryFilter, lowStockOnly], load)

function isLow(i) {
  return i.reorder_level != null && (i.quantity_on_hand || 0) <= i.reorder_level
}

const dialogOpen = ref(false)
const editing = ref(null)
const form = reactive({ item_name: '', category: 'linen', quantity_on_hand: 0, reorder_level: null, unit: '' })
const saving = computed(() => createItem.loading || updateItem.loading)
const actionError = computed(() => createItem.error?.messages?.[0] || updateItem.error?.messages?.[0])

function openNewItem() {
  editing.value = null
  Object.assign(form, { item_name: '', category: 'linen', quantity_on_hand: 0, reorder_level: null, unit: '' })
  createItem.error = null
  dialogOpen.value = true
}
function openEditItem(i) {
  editing.value = i
  Object.assign(form, {
    item_name: i.item_name,
    category: i.category,
    quantity_on_hand: i.quantity_on_hand,
    reorder_level: i.reorder_level,
    unit: i.unit || '',
  })
  updateItem.error = null
  dialogOpen.value = true
}
function save() {
  if (editing.value) {
    updateItem.submit(
      { name: editing.value.name, quantity_on_hand: form.quantity_on_hand, reorder_level: form.reorder_level, unit: form.unit || undefined },
      { onSuccess: () => { dialogOpen.value = false; load() } },
    )
  } else {
    createItem.submit(
      { item_name: form.item_name, category: form.category, quantity_on_hand: form.quantity_on_hand, reorder_level: form.reorder_level, unit: form.unit || undefined },
      { onSuccess: () => { dialogOpen.value = false; load() } },
    )
  }
}
</script>
