<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('complaints.title') }}</h1>
      <select v-model="statusFilter" class="select-field">
        <option value="">{{ $t('common.allStatuses') }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
    </div>

    <p v-if="complaints.error" class="text-sm text-red-600">{{ complaints.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('complaints.guestCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.categoryCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.descriptionCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.priorityCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.dueCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.raisedCol') }}</th>
            <th class="px-4 py-3">{{ $t('complaints.statusCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="complaints.loading && !complaints.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="8">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!complaints.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="8">{{ $t('complaints.noneMatch') }}</td>
          </tr>
          <tr v-for="c in complaints.data" :key="c.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
              <RouterLink :to="{ name: 'GuestDetail', params: { id: c.guest } }" class="hover:underline">{{ c.guest }}</RouterLink>
            </td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ statusLabel(c.category) }}</td>
            <td class="max-w-xs truncate px-4 py-3 text-gray-500 dark:text-gray-400">{{ c.description }}</td>
            <td class="px-4 py-3"><StatusBadge :status="c.priority" /></td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ c.due_by ? formatDateTime(c.due_by) : '—' }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDateTime(c.raised_at) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="c.status" /></td>
            <td class="px-4 py-3 text-right">
              <div v-if="c.status !== 'resolved'" class="flex justify-end gap-2">
                <Button size="sm" variant="outline" theme="green" @click="openResolve(c)">{{ $t('complaints.resolveBtn') }}</Button>
                <Button v-if="c.status !== 'escalated'" size="sm" variant="outline" theme="red" @click="doUpdate(c.name, 'escalated')">
                  {{ $t('complaints.escalateBtn') }}
                </Button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="resolveOpen" :options="{ title: $t('complaints.resolveDialogTitle') }">
      <template #body-content>
        <Field :label="$t('complaints.resolutionField')">
          <textarea v-model="resolution" rows="3" class="input-field" />
        </Field>
        <p v-if="update.error" class="mt-3 text-sm text-red-600">{{ update.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="resolveOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!resolution" :loading="update.loading" @click="submitResolve">{{ $t('complaints.resolveBtn2') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import { complaintsResource, updateComplaintStatusResource } from '@/api/crm'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['open', 'in_progress', 'resolved', 'escalated']

const statusFilter = ref('')
const complaints = complaintsResource()
const update = updateComplaintStatusResource()

function load() {
  complaints.fetch({ status: statusFilter.value || undefined })
}
onMounted(load)
watch(statusFilter, load)

const resolveOpen = ref(false)
const resolution = ref('')
const resolvingName = ref('')
function openResolve(c) {
  resolvingName.value = c.name
  resolution.value = ''
  update.error = null
  resolveOpen.value = true
}
function submitResolve() {
  update.submit(
    { name: resolvingName.value, status: 'resolved', resolution: resolution.value },
    { onSuccess: () => { resolveOpen.value = false; load() } },
  )
}
function doUpdate(name, status) {
  update.submit({ name, status }, { onSuccess: load })
}
</script>
