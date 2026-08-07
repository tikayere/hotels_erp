<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('leave.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="statusFilter" class="select-field">
          <option value="">{{ $t('common.allStatuses') }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <Button variant="solid" @click="openNew">{{ $t('leave.newApplication') }}</Button>
      </div>
    </div>

    <p v-if="leaves.error" class="text-sm text-red-600">{{ leaves.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('leave.staffCol') }}</th>
            <th class="px-4 py-3">{{ $t('leave.typeCol') }}</th>
            <th class="px-4 py-3">{{ $t('leave.datesCol') }}</th>
            <th class="px-4 py-3">{{ $t('leave.statusCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="leaves.loading && !leaves.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!leaves.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('leave.noneMatch') }}</td>
          </tr>
          <tr v-for="l in leaves.data" :key="l.name">
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ l.staff_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ statusLabel(l.leave_type) }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDate(l.from_date) }} → {{ formatDate(l.to_date) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="l.status" /></td>
            <td class="px-4 py-3 text-right">
              <div v-if="l.status === 'pending'" class="flex justify-end gap-2">
                <Button size="sm" variant="outline" theme="green" @click="doApprove(l.name)">{{ $t('leave.approveBtn') }}</Button>
                <Button size="sm" variant="outline" theme="red" @click="doReject(l.name)">{{ $t('leave.rejectBtn') }}</Button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="newOpen" :options="{ title: $t('leave.newDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('leave.staffField')">
            <input v-model="form.staff" type="text" :placeholder="$t('leave.staffPlaceholder')" class="input-field" />
          </Field>
          <Field :label="$t('leave.leaveTypeField')">
            <select v-model="form.leave_type" class="select-field w-full">
              <option v-for="t in LEAVE_TYPES" :key="t" :value="t">{{ statusLabel(t) }}</option>
            </select>
          </Field>
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('leave.fromField')">
              <input v-model="form.from_date" type="date" class="input-field" />
            </Field>
            <Field :label="$t('leave.toField')">
              <input v-model="form.to_date" type="date" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('leave.reasonOptionalField')">
            <textarea v-model="form.reason" rows="2" class="input-field" />
          </Field>
        </div>
        <p v-if="createLeave.error" class="mt-3 text-sm text-red-600">{{ createLeave.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="newOpen = false">{{ $t('common.cancel') }}</Button>
          <Button
            variant="solid"
            :disabled="!form.staff || !form.from_date || !form.to_date"
            :loading="createLeave.loading"
            @click="submitNew"
          >
            {{ $t('leave.submitBtn') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { approveLeaveResource, createLeaveApplicationResource, leaveApplicationsResource, rejectLeaveResource } from '@/api/hr'
import { formatDate, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const STATUSES = ['pending', 'approved', 'rejected']
const LEAVE_TYPES = ['annual', 'sick', 'unpaid', 'maternity_paternity']

const statusFilter = ref('')
const leaves = leaveApplicationsResource()
const createLeave = createLeaveApplicationResource()
const approveLeave = approveLeaveResource()
const rejectLeave = rejectLeaveResource()

const newOpen = ref(false)
const form = reactive({ staff: '', leave_type: 'annual', from_date: '', to_date: '', reason: '' })

function load() {
  leaves.fetch({ status: statusFilter.value || undefined })
}
onMounted(load)
watch(statusFilter, load)

function openNew() {
  Object.assign(form, { staff: '', leave_type: 'annual', from_date: '', to_date: '', reason: '' })
  createLeave.error = null
  newOpen.value = true
}

function submitNew() {
  createLeave.submit(
    { staff: form.staff, leave_type: form.leave_type, from_date: form.from_date, to_date: form.to_date, reason: form.reason || undefined },
    { onSuccess: () => { newOpen.value = false; load() } },
  )
}

function doApprove(name) {
  approveLeave.submit({ name }, { onSuccess: load })
}
function doReject(name) {
  rejectLeave.submit({ name }, { onSuccess: load })
}
</script>
