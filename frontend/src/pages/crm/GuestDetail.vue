<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'Guests' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('guestDetail.backLink') }}
    </RouterLink>

    <p v-if="guest.error" class="text-sm text-red-600">{{ guest.error.messages?.[0] || $t('guestDetail.failedToLoad') }}</p>
    <div v-if="guest.loading && !guest.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="guest.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xl font-semibold text-gray-900 dark:text-gray-100">{{ guest.data.guest_name }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">{{ guest.data.phone || '—' }} · {{ guest.data.email || '—' }}</div>
        </div>
        <span v-if="guest.data.vip_status" class="text-sm font-medium text-amber-600 dark:text-amber-400">{{ $t('guests.vip') }}</span>
      </div>

      <Card :title="$t('guestDetail.communicationsTitle')">
        <template #actions>
          <Button size="sm" variant="outline" @click="openLogComm">{{ $t('guestDetail.logBtn') }}</Button>
        </template>
        <ul v-if="guest.data.communications?.length" class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <li v-for="c in guest.data.communications" :key="c.name" class="py-2">
            <div class="flex items-center justify-between">
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ c.subject || statusLabel(c.channel) }}</span>
              <span class="text-xs text-gray-400">{{ formatDateTime(c.sent_at) }}</span>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{{ statusLabel(c.direction) }} · {{ statusLabel(c.channel) }}</div>
            <p v-if="c.message" class="mt-1 text-gray-700 dark:text-gray-300">{{ c.message }}</p>
          </li>
        </ul>
        <p v-else class="text-sm text-gray-500 dark:text-gray-400">{{ $t('guestDetail.noCommunications') }}</p>
      </Card>

      <Card :title="$t('guestDetail.complaintsTitle')">
        <template #actions>
          <Button size="sm" variant="outline" @click="openNewComplaint">{{ $t('guestDetail.newBtn') }}</Button>
        </template>
        <ul v-if="guest.data.complaints?.length" class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <li v-for="c in guest.data.complaints" :key="c.name" class="py-2">
            <div class="flex items-center justify-between">
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ statusLabel(c.category) || $t('guestDetail.complaint') }}</span>
              <div class="flex items-center gap-2">
                <StatusBadge :status="c.priority" />
                <StatusBadge :status="c.status" />
              </div>
            </div>
            <p class="mt-1 text-gray-700 dark:text-gray-300">{{ c.description }}</p>
          </li>
        </ul>
        <p v-else class="text-sm text-gray-500 dark:text-gray-400">{{ $t('guestDetail.noComplaints') }}</p>
      </Card>
    </template>

    <Dialog v-model="commOpen" :options="{ title: $t('guestDetail.logCommDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('guestDetail.channelField')">
              <select v-model="commForm.channel" class="select-field w-full">
                <option v-for="c in CHANNELS" :key="c" :value="c">{{ statusLabel(c) }}</option>
              </select>
            </Field>
            <Field :label="$t('guestDetail.directionField')">
              <select v-model="commForm.direction" class="select-field w-full">
                <option value="inbound">{{ $t('guestDetail.inbound') }}</option>
                <option value="outbound">{{ $t('guestDetail.outbound') }}</option>
              </select>
            </Field>
          </div>
          <Field :label="$t('guestDetail.subjectOptionalField')">
            <input v-model="commForm.subject" type="text" class="input-field" />
          </Field>
          <Field :label="$t('guestDetail.messageOptionalField')">
            <textarea v-model="commForm.message" rows="2" class="input-field" />
          </Field>
        </div>
        <p v-if="createComm.error" class="mt-3 text-sm text-red-600">{{ createComm.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="commOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :loading="createComm.loading" @click="submitComm">{{ $t('guestDetail.logBtn2') }}</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="complaintOpen" :options="{ title: $t('guestDetail.newComplaintDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('guestDetail.categoryField')">
              <select v-model="complaintForm.category" class="select-field w-full">
                <option v-for="c in CATEGORIES" :key="c" :value="c">{{ statusLabel(c) }}</option>
              </select>
            </Field>
            <Field :label="$t('guestDetail.priorityField')">
              <select v-model="complaintForm.priority" class="select-field w-full">
                <option v-for="p in PRIORITIES" :key="p" :value="p">{{ statusLabel(p) }}</option>
              </select>
            </Field>
          </div>
          <Field :label="$t('guestDetail.reservationOptionalField')">
            <input v-model="complaintForm.reservation" type="text" placeholder="RES-00001" class="input-field" />
          </Field>
          <Field :label="$t('guestDetail.descriptionField')">
            <textarea v-model="complaintForm.description" rows="3" class="input-field" />
          </Field>
        </div>
        <p v-if="createComplaint.error" class="mt-3 text-sm text-red-600">{{ createComplaint.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="complaintOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!complaintForm.description" :loading="createComplaint.loading" @click="submitComplaint">
            {{ $t('guestDetail.logComplaintBtn') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import { createCommunicationResource, createComplaintResource, guestResource } from '@/api/crm'
import { formatDateTime, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import Field from '@/components/Field.vue'
import Card from '@/components/Card.vue'

const CHANNELS = ['email', 'phone', 'sms', 'in_person']
const CATEGORIES = ['room', 'service', 'billing', 'cleanliness', 'noise', 'other']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']

const props = defineProps({ id: { type: String, required: true } })

const guest = guestResource()
const createComm = createCommunicationResource()
const createComplaint = createComplaintResource()

function load() {
  guest.fetch({ name: props.id })
}
onMounted(load)
watch(() => props.id, load)

const commOpen = ref(false)
const commForm = reactive({ channel: 'phone', direction: 'outbound', subject: '', message: '' })
function openLogComm() {
  Object.assign(commForm, { channel: 'phone', direction: 'outbound', subject: '', message: '' })
  createComm.error = null
  commOpen.value = true
}
function submitComm() {
  createComm.submit(
    { guest: props.id, ...commForm, subject: commForm.subject || undefined, message: commForm.message || undefined },
    { onSuccess: () => { commOpen.value = false; load() } },
  )
}

const complaintOpen = ref(false)
const complaintForm = reactive({ category: 'room', priority: 'medium', reservation: '', description: '' })
function openNewComplaint() {
  Object.assign(complaintForm, { category: 'room', priority: 'medium', reservation: '', description: '' })
  createComplaint.error = null
  complaintOpen.value = true
}
function submitComplaint() {
  createComplaint.submit(
    {
      guest: props.id,
      category: complaintForm.category,
      priority: complaintForm.priority,
      description: complaintForm.description,
      reservation: complaintForm.reservation || undefined,
    },
    { onSuccess: () => { complaintOpen.value = false; load() } },
  )
}
</script>
