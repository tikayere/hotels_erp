<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('suppliers.title') }}</h1>
      <Button v-if="canWrite" variant="solid" @click="openNew">{{ $t('suppliers.newSupplier') }}</Button>
    </div>

    <p v-if="suppliers.error" class="text-sm text-red-600">{{ suppliers.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="s in suppliers.data"
        :key="s.name"
        class="flex flex-col gap-1 rounded-lg border border-gray-100 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
      >
        <div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ s.supplier_name }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">{{ s.contact_person || '—' }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">{{ s.phone || s.email || $t('common.noContact') }}</div>
        <div class="text-xs text-gray-400">{{ statusLabel(s.category) }}</div>
      </div>
      <p v-if="!suppliers.loading && !suppliers.data?.length" class="text-sm text-gray-500 dark:text-gray-400">
        {{ $t('suppliers.noSuppliersYet') }}
      </p>
    </div>

    <Dialog v-model="newOpen" :options="{ title: $t('suppliers.newDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('suppliers.supplierNameField')">
            <input v-model="form.supplier_name" type="text" class="input-field" />
          </Field>
          <Field :label="$t('suppliers.contactPersonField')">
            <input v-model="form.contact_person" type="text" class="input-field" />
          </Field>
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('suppliers.phoneField')">
              <input v-model="form.phone" type="text" class="input-field" />
            </Field>
            <Field :label="$t('suppliers.emailField')">
              <input v-model="form.email" type="text" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('suppliers.categoryField')">
            <select v-model="form.category" class="select-field w-full">
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ statusLabel(c) }}</option>
            </select>
          </Field>
        </div>
        <p v-if="createSupplier.error" class="mt-3 text-sm text-red-600">{{ createSupplier.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!form.supplier_name" :loading="createSupplier.loading" @click="submit">
            {{ $t('suppliers.createBtn') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { createSupplierResource, suppliersResource } from '@/api/inventory'
import { boot } from '@/session'
import { statusLabel } from '@/utils/format'
import Field from '@/components/Field.vue'

const CATEGORIES = ['linen', 'cleaning_supplies', 'food', 'maintenance_supplies', 'other']

const suppliers = suppliersResource()
const createSupplier = createSupplierResource()
const canWrite = computed(() => (boot.data?.roles || []).includes('System Manager'))

function load() {
  suppliers.fetch({})
}
onMounted(load)

const newOpen = ref(false)
const form = reactive({ supplier_name: '', contact_person: '', phone: '', email: '', category: 'linen' })
function openNew() {
  Object.assign(form, { supplier_name: '', contact_person: '', phone: '', email: '', category: 'linen' })
  createSupplier.error = null
  newOpen.value = true
}
function submit() {
  createSupplier.submit(
    { ...form, contact_person: form.contact_person || undefined, phone: form.phone || undefined, email: form.email || undefined },
    { onSuccess: () => { newOpen.value = false; load() } },
  )
}
</script>
