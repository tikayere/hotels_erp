<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'Maintenance' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('maintenanceDetail.backLink') }}
    </RouterLink>

    <p v-if="request.error" class="text-sm text-red-600">{{ request.error.messages?.[0] || $t('maintenanceDetail.failedToLoad') }}</p>
    <div v-if="request.loading && !request.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="request.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">
            {{ $t('maintenanceDetail.roomPrefix') }} {{ request.data.room_number || request.data.room || '—' }}
          </div>
          <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ request.data.issue }}</div>
        </div>
        <div class="flex flex-col items-end gap-2">
          <StatusBadge :status="request.data.status" />
          <StatusBadge :status="request.data.priority" />
        </div>
      </div>

      <Card>
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <InfoRow :label="$t('maintenanceDetail.technicianLabel')" :value="request.data.technician || $t('common.unassigned')" />
          <InfoRow :label="$t('maintenanceDetail.openedLabel')" :value="formatDateTime(request.data.opened_at)" />
          <InfoRow :label="$t('maintenanceDetail.closedLabel')" :value="formatDateTime(request.data.closed_at)" />
        </div>
      </Card>

      <div class="flex flex-wrap items-center gap-2">
        <input v-model="technician" type="text" :placeholder="$t('maintenanceDetail.assignTechPlaceholder')" class="input-field w-56" />
        <Button variant="outline" :disabled="!technician" :loading="assign.loading" @click="doAssign">{{ $t('maintenanceDetail.assignBtn') }}</Button>
        <Button
          v-if="['open', 'assigned'].includes(request.data.status)"
          variant="solid"
          :loading="start.loading"
          @click="doStart"
        >
          {{ $t('maintenanceDetail.startBtn') }}
        </Button>
        <Button
          v-if="['open', 'assigned', 'in_progress'].includes(request.data.status)"
          variant="solid"
          theme="green"
          :loading="resolve.loading"
          @click="doResolve"
        >
          {{ $t('maintenanceDetail.resolveBtn') }}
        </Button>
        <template v-if="request.data.status === 'resolved'">
          <input v-model.number="cost" type="number" min="0" :placeholder="$t('maintenanceDetail.costPlaceholder')" class="input-field w-32" />
          <input v-model="costCurrency" type="text" placeholder="USD" class="input-field w-20" />
          <Button variant="outline" :loading="close.loading" @click="doClose">
            {{ $t('maintenanceDetail.closeBtn') }}
          </Button>
        </template>
      </div>
      <p v-if="request.data.cost_minor" class="text-sm text-gray-500 dark:text-gray-400">
        {{ $t('maintenanceDetail.costLabel') }} {{ formatMoney(request.data.cost_minor, request.data.currency) }}
      </p>
      <p v-if="actionError" class="text-sm text-red-600">{{ actionError }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import {
  assignRequestResource,
  closeRequestResource,
  requestResource,
  resolveRequestResource,
  startRequestResource,
} from '@/api/maintenance'
import { formatDateTime, formatMoney } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import InfoRow from '@/components/InfoRow.vue'
import Card from '@/components/Card.vue'

const props = defineProps({ id: { type: String, required: true } })

const request = requestResource()
const assign = assignRequestResource()
const start = startRequestResource()
const resolve = resolveRequestResource()
const close = closeRequestResource()
const technician = ref('')
const cost = ref(null)
const costCurrency = ref('')

const actionError = computed(
  () => assign.error?.messages?.[0] || start.error?.messages?.[0] || resolve.error?.messages?.[0] || close.error?.messages?.[0],
)

function load() {
  request.fetch({ name: props.id })
}

onMounted(load)
watch(() => props.id, load)

function doAssign() {
  assign.submit({ name: props.id, technician: technician.value }, { onSuccess: () => { technician.value = ''; load() } })
}
function doStart() {
  start.submit({ name: props.id }, { onSuccess: load })
}
function doResolve() {
  resolve.submit({ name: props.id }, { onSuccess: load })
}
function doClose() {
  close.submit(
    { name: props.id, cost_minor: cost.value || undefined, currency: cost.value ? costCurrency.value : undefined },
    { onSuccess: load },
  )
}
</script>
