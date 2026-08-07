<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('staff.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <input v-model="search" type="search" :placeholder="$t('staff.searchPlaceholder')" class="input-field w-48" />
        <select v-model="departmentFilter" class="select-field">
          <option value="">{{ $t('staff.allDepartments') }}</option>
          <option v-for="d in DEPARTMENTS" :key="d" :value="d">{{ departmentLabel(d) }}</option>
        </select>
        <Button variant="solid" @click="openNewStaff">{{ $t('staff.addStaff') }}</Button>
      </div>
    </div>

    <p v-if="staffList.error" class="text-sm text-red-600">{{ staffList.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('staff.nameCol') }}</th>
            <th class="px-4 py-3">{{ $t('staff.departmentCol') }}</th>
            <th class="px-4 py-3">{{ $t('staff.designationCol') }}</th>
            <th class="px-4 py-3">{{ $t('staff.contactCol') }}</th>
            <th class="px-4 py-3">{{ $t('staff.statusCol') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="staffList.loading && !staffList.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!staffList.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="5">{{ $t('staff.noneMatch') }}</td>
          </tr>
          <tr
            v-for="s in staffList.data"
            :key="s.name"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60"
            @click="openEditStaff(s)"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{{ s.employee_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ departmentLabel(s.department) }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ s.designation || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ s.phone || s.email || '—' }}</td>
            <td class="px-4 py-3"><StatusBadge :status="s.status" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="dialogOpen" :options="{ title: editing ? $t('staff.editDialogTitle', { name: editing.employee_name }) : $t('staff.addDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field v-if="!editing" :label="$t('staff.employeeNameField')">
            <input v-model="form.employee_name" type="text" class="input-field" />
          </Field>
          <Field :label="$t('staff.departmentField')">
            <select v-model="form.department" class="select-field w-full">
              <option v-for="d in DEPARTMENTS" :key="d" :value="d">{{ departmentLabel(d) }}</option>
            </select>
          </Field>
          <Field :label="$t('staff.designationField')">
            <input v-model="form.designation" type="text" class="input-field" />
          </Field>
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('staff.phoneField')">
              <input v-model="form.phone" type="text" class="input-field" />
            </Field>
            <Field :label="$t('staff.emailField')">
              <input v-model="form.email" type="text" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('staff.dailyRateField')">
            <input v-model.number="form.daily_rate_minor" type="number" min="0" class="input-field" />
          </Field>
          <Field :label="$t('staff.linkedUserField')">
            <input v-model="form.user" type="text" placeholder="user@example.com" class="input-field" />
          </Field>
          <Field v-if="editing" :label="$t('staff.statusField')">
            <select v-model="form.status" class="select-field w-full">
              <option v-for="s in STATUSES" :key="s" :value="s">{{ statusLabel(s) }}</option>
            </select>
          </Field>
        </div>
        <p v-if="actionError" class="mt-3 text-sm text-red-600">{{ actionError }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="dialogOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :loading="saving" @click="save">{{ editing ? $t('staff.saveBtn') : $t('staff.addStaffBtn') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { createStaffResource, staffListResource, updateStaffResource } from '@/api/hr'
import { departmentLabel, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'

const DEPARTMENTS = ['Front Desk', 'Housekeeping', 'Maintenance', 'Restaurant', 'Finance', 'HR', 'Management']
const STATUSES = ['active', 'on_leave', 'terminated']

const search = ref('')
const departmentFilter = ref('')
const staffList = staffListResource()
const createStaff = createStaffResource()
const updateStaff = updateStaffResource()

const dialogOpen = ref(false)
const editing = ref(null)
const form = reactive({
  employee_name: '',
  department: 'Front Desk',
  designation: '',
  phone: '',
  email: '',
  daily_rate_minor: null,
  user: '',
  status: 'active',
})

const saving = computed(() => createStaff.loading || updateStaff.loading)
const actionError = computed(() => createStaff.error?.messages?.[0] || updateStaff.error?.messages?.[0])

let searchDebounce
function load() {
  staffList.fetch({ department: departmentFilter.value || undefined, search: search.value || undefined })
}
onMounted(load)
watch(departmentFilter, load)
watch(search, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(load, 300)
})

function openNewStaff() {
  editing.value = null
  Object.assign(form, {
    employee_name: '',
    department: 'Front Desk',
    designation: '',
    phone: '',
    email: '',
    daily_rate_minor: null,
    user: '',
    status: 'active',
  })
  createStaff.error = null
  dialogOpen.value = true
}

function openEditStaff(s) {
  editing.value = s
  Object.assign(form, {
    employee_name: s.employee_name,
    department: s.department,
    designation: s.designation || '',
    phone: s.phone || '',
    email: s.email || '',
    daily_rate_minor: s.daily_rate_minor,
    user: s.user || '',
    status: s.status,
  })
  updateStaff.error = null
  dialogOpen.value = true
}

function save() {
  if (editing.value) {
    updateStaff.submit(
      {
        name: editing.value.name,
        status: form.status,
        department: form.department,
        designation: form.designation || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        daily_rate_minor: form.daily_rate_minor,
        user: form.user || undefined,
      },
      { onSuccess: () => { dialogOpen.value = false; load() } },
    )
  } else {
    createStaff.submit(
      {
        employee_name: form.employee_name,
        department: form.department,
        designation: form.designation || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        daily_rate_minor: form.daily_rate_minor,
        user: form.user || undefined,
      },
      { onSuccess: () => { dialogOpen.value = false; load() } },
    )
  }
}
</script>
