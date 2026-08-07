<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('housekeeping.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">{{ $t('common.allStatuses') }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <label class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <input v-model="mineOnly" type="checkbox" class="rounded border-gray-300" />
          {{ $t('housekeeping.myTasks') }}
        </label>
        <Button variant="solid" @click="openNewTask">{{ $t('housekeeping.newTask') }}</Button>
      </div>
    </div>

    <p v-if="tasks.error" class="text-sm text-red-600">{{ tasks.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div v-if="tasks.loading && !tasks.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>
    <div v-else-if="!tasks.data?.length" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('housekeeping.noneMatch') }}</div>

    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="t in tasks.data"
        :key="t.name"
        :to="{ name: 'HousekeepingTaskDetail', params: { id: t.name } }"
        class="flex flex-col gap-2 rounded-lg border border-gray-100 bg-white p-4 transition hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700"
      >
        <div class="flex items-start justify-between">
          <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ $t('housekeeping.roomPrefix') }} {{ t.room_number || t.room }}</span>
          <StatusBadge :status="t.status" />
        </div>
        <div class="text-xs text-gray-500 dark:text-gray-400">{{ statusLabel(t.type) }} · {{ $t('housekeeping.floorPrefix') }} {{ t.floor || '—' }}</div>
        <div class="text-xs text-gray-600 dark:text-gray-300">
          {{ $t('housekeeping.duePrefix') }} {{ formatDateTime(t.due_at) }}
        </div>
        <div class="text-xs text-gray-400">{{ t.assigned_to || $t('common.unassigned') }}</div>
      </RouterLink>
    </div>

    <Dialog v-model="newTaskOpen" :options="{ title: $t('housekeeping.newTaskDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('housekeeping.roomField')">
            <input v-model="form.room" type="text" :placeholder="$t('housekeeping.roomPlaceholder')" class="input-field" />
          </Field>
          <Field :label="$t('housekeeping.typeField')">
            <select v-model="form.type" class="select-field w-full">
              <option v-for="t in TYPES" :key="t" :value="t">{{ statusLabel(t) }}</option>
            </select>
          </Field>
          <Field :label="$t('housekeeping.assignToField')">
            <input v-model="form.assigned_to" type="text" placeholder="user@example.com" class="input-field" />
          </Field>
          <Field :label="$t('housekeeping.notesField')">
            <textarea v-model="form.notes" rows="2" class="input-field" />
          </Field>
        </div>
        <p v-if="createTask.error" class="mt-3 text-sm text-red-600">{{ createTask.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newTaskOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!form.room" :loading="createTask.loading" @click="submitNewTask">
            {{ $t('housekeeping.createTask') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { RouterLink, useRouter } from 'vue-router'
import { createTaskResource, tasksResource } from '@/api/housekeeping'
import { activeProperty } from '@/property'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['pending', 'in_progress', 'completed', 'verified']
const TYPES = ['cleaning', 'inspection', 'turndown', 'deep_clean', 'laundry']

const router = useRouter()
const statusFilter = ref('')
const mineOnly = ref(false)
const tasks = tasksResource()
const createTask = createTaskResource()
const newTaskOpen = ref(false)
const form = reactive({ room: '', type: 'cleaning', assigned_to: '', notes: '' })

function load() {
  tasks.fetch({
    property: activeProperty.value || undefined,
    status: statusFilter.value || undefined,
    mine: mineOnly.value || undefined,
  })
}

onMounted(load)
watch([activeProperty, statusFilter, mineOnly], load)

function openNewTask() {
  Object.assign(form, { room: '', type: 'cleaning', assigned_to: '', notes: '' })
  createTask.error = null
  newTaskOpen.value = true
}

function submitNewTask() {
  createTask.submit(
    { room: form.room, type: form.type, assigned_to: form.assigned_to || undefined, notes: form.notes || undefined },
    {
      onSuccess(task) {
        newTaskOpen.value = false
        router.push({ name: 'HousekeepingTaskDetail', params: { id: task.name } })
      },
    },
  )
}
</script>
