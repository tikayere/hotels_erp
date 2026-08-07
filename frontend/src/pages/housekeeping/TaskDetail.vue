<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'Housekeeping' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('housekeepingDetail.backLink') }}
    </RouterLink>

    <p v-if="task.error" class="text-sm text-red-600">{{ task.error.messages?.[0] || $t('housekeepingDetail.failedToLoad') }}</p>
    <div v-if="task.loading && !task.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="task.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t('housekeepingDetail.roomPrefix') }} {{ task.data.room_number || task.data.room }}</div>
          <div class="text-xl font-semibold text-gray-900 dark:text-gray-100">{{ statusLabel(task.data.type) }}</div>
        </div>
        <StatusBadge :status="task.data.status" />
      </div>

      <Card>
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <InfoRow :label="$t('housekeepingDetail.floorLabel')" :value="task.data.floor" />
          <InfoRow :label="$t('housekeepingDetail.assignedToLabel')" :value="task.data.assigned_to || $t('common.unassigned')" />
          <InfoRow :label="$t('housekeepingDetail.dueLabel')" :value="formatDateTime(task.data.due_at)" />
        </div>
        <p v-if="task.data.notes" class="mt-4 text-sm text-gray-700 dark:text-gray-300">{{ task.data.notes }}</p>
      </Card>

      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="assignee"
          type="text"
          :placeholder="$t('housekeepingDetail.reassignPlaceholder')"
          class="input-field w-56"
        />
        <Button variant="outline" :disabled="!assignee" :loading="assign.loading" @click="doAssign">{{ $t('housekeepingDetail.assignBtn') }}</Button>
        <Button v-if="task.data.status === 'pending'" variant="solid" :loading="start.loading" @click="doStart">
          {{ $t('housekeepingDetail.startBtn') }}
        </Button>
        <Button v-if="task.data.status === 'in_progress'" variant="solid" :loading="complete.loading" @click="doComplete">
          {{ $t('housekeepingDetail.markCompletedBtn') }}
        </Button>
        <Button v-if="task.data.status === 'completed'" variant="solid" theme="green" :loading="verify.loading" @click="doVerify">
          {{ $t('housekeepingDetail.verifyBtn') }}
        </Button>
      </div>
      <p v-if="actionError" class="text-sm text-red-600">{{ actionError }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import {
  assignTaskResource,
  completeTaskResource,
  startTaskResource,
  taskResource,
  verifyTaskResource,
} from '@/api/housekeeping'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import InfoRow from '@/components/InfoRow.vue'
import Card from '@/components/Card.vue'

const props = defineProps({ id: { type: String, required: true } })

const task = taskResource()
const assign = assignTaskResource()
const start = startTaskResource()
const complete = completeTaskResource()
const verify = verifyTaskResource()
const assignee = ref('')

const actionError = computed(
  () => assign.error?.messages?.[0] || start.error?.messages?.[0] || complete.error?.messages?.[0] || verify.error?.messages?.[0],
)

function load() {
  task.fetch({ name: props.id })
}

onMounted(load)
watch(() => props.id, load)

function doAssign() {
  assign.submit({ name: props.id, assigned_to: assignee.value }, { onSuccess: () => { assignee.value = ''; load() } })
}
function doStart() {
  start.submit({ name: props.id }, { onSuccess: load })
}
function doComplete() {
  complete.submit({ name: props.id }, { onSuccess: load })
}
function doVerify() {
  verify.submit({ name: props.id }, { onSuccess: load })
}
</script>
