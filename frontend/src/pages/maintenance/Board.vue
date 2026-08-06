<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Maintenance</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">All statuses</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <select v-model="priorityFilter" class="select-field">
          <option value="">All priorities</option>
          <option v-for="p in PRIORITIES" :key="p" :value="p">{{ statusLabel(p) }}</option>
        </select>
        <Button variant="solid" @click="openNewRequest">+ New Request</Button>
      </div>
    </div>

    <p v-if="requests.error" class="text-sm text-red-600">{{ requests.error.messages?.[0] || 'Failed to load' }}</p>
    <div v-if="requests.loading && !requests.data" class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    <div v-else-if="!requests.data?.length" class="text-sm text-gray-500 dark:text-gray-400">No requests match these filters.</div>

    <div v-else class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">Room</th>
            <th class="px-4 py-3">Issue</th>
            <th class="px-4 py-3">Priority</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Technician</th>
            <th class="px-4 py-3">Opened</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr
            v-for="r in requests.data"
            :key="r.name"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60"
            @click="$router.push({ name: 'MaintenanceRequestDetail', params: { id: r.name } })"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ r.room_number || r.room || '—' }}</td>
            <td class="max-w-xs truncate px-4 py-3 text-gray-700 dark:text-gray-300">{{ r.issue }}</td>
            <td class="px-4 py-3"><StatusBadge :status="r.priority" /></td>
            <td class="px-4 py-3"><StatusBadge :status="r.status" /></td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ r.technician || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDateTime(r.opened_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="newRequestOpen" :options="{ title: 'New Maintenance Request' }">
      <template #body-content>
        <div class="space-y-3">
          <Field label="Room (optional)">
            <input v-model="form.room" type="text" placeholder="Room docname (e.g. RM-0001)" class="input-field" />
          </Field>
          <Field label="Issue">
            <textarea v-model="form.issue" rows="2" class="input-field" />
          </Field>
          <Field label="Priority">
            <select v-model="form.priority" class="select-field w-full">
              <option v-for="p in PRIORITIES" :key="p" :value="p">{{ statusLabel(p) }}</option>
            </select>
          </Field>
        </div>
        <p v-if="createRequest.error" class="mt-3 text-sm text-red-600">{{ createRequest.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newRequestOpen = false">Cancel</Button>
          <Button variant="solid" :disabled="!form.issue" :loading="createRequest.loading" @click="submitNewRequest">
            Create Request
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { createRequestResource, requestsResource } from '@/api/maintenance'
import { activeProperty } from '@/property'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['open', 'assigned', 'in_progress', 'resolved', 'closed']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']

const router = useRouter()
const statusFilter = ref('')
const priorityFilter = ref('')
const requests = requestsResource()
const createRequest = createRequestResource()
const newRequestOpen = ref(false)
const form = reactive({ room: '', issue: '', priority: 'medium' })

function load() {
  requests.fetch({
    property: activeProperty.value || undefined,
    status: statusFilter.value || undefined,
    priority: priorityFilter.value || undefined,
  })
}

onMounted(load)
watch([activeProperty, statusFilter, priorityFilter], load)

function openNewRequest() {
  Object.assign(form, { room: '', issue: '', priority: 'medium' })
  createRequest.error = null
  newRequestOpen.value = true
}

function submitNewRequest() {
  createRequest.submit(
    { room: form.room || undefined, issue: form.issue, priority: form.priority },
    {
      onSuccess(req) {
        newRequestOpen.value = false
        router.push({ name: 'MaintenanceRequestDetail', params: { id: req.name } })
      },
    },
  )
}
</script>
