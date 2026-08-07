<template>
  <div class="max-w-3xl space-y-6">
    <RouterLink :to="{ name: 'Reservations' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('reservationDetail.backLink') }}
    </RouterLink>

    <p v-if="reservation.error" class="text-sm text-red-600">
      {{ reservation.error.messages?.[0] || $t('reservationDetail.failedToLoad') }}
    </p>
    <div v-if="reservation.loading && !reservation.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="reservation.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t('reservationDetail.confirmationNumber') }}</div>
          <div class="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {{ reservation.data.confirmation_number }}
          </div>
        </div>
        <StatusBadge :status="reservation.data.status" />
      </div>

      <div class="grid grid-cols-2 gap-x-6 gap-y-4 rounded-lg border border-gray-100 bg-white p-5 sm:grid-cols-3 dark:border-gray-800 dark:bg-gray-900">
        <InfoRow :label="$t('reservationDetail.roomType')" :value="reservation.data.room_type?.room_type_name" />
        <InfoRow :label="$t('reservationDetail.ratePlan')" :value="reservation.data.rate_plan?.plan_name" />
        <InfoRow :label="$t('reservationDetail.rooms')" :value="reservation.data.rooms_requested" />
        <InfoRow :label="$t('reservationDetail.checkIn')" :value="formatDate(reservation.data.check_in)" />
        <InfoRow :label="$t('reservationDetail.checkOut')" :value="formatDate(reservation.data.check_out)" />
        <InfoRow
          :label="$t('reservationDetail.total')"
          :value="formatMoney(reservation.data.total_amount_minor, reservation.data.currency)"
        />
        <InfoRow v-if="reservation.data.payment_reference" :label="$t('reservationDetail.paymentRef')" :value="reservation.data.payment_reference" />
        <InfoRow :label="$t('reservationDetail.booked')" :value="formatDateTime(reservation.data.created_at)" />
      </div>

      <div class="rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <h2 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">{{ $t('reservationDetail.guestsTitle') }}</h2>
        <ul class="space-y-1 text-sm text-gray-700 dark:text-gray-300">
          <li v-for="(g, i) in reservation.data.guests" :key="i">
            {{ g.guest_name }}
            <span v-if="g.phone" class="text-gray-400"> · {{ g.phone }}</span>
            <span v-if="g.email" class="text-gray-400"> · {{ g.email }}</span>
          </li>
        </ul>
      </div>

      <div
        v-if="reservation.data.room_assignment"
        class="rounded-lg border border-gray-100 bg-white p-5 text-sm text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300"
      >
        <span class="font-medium text-gray-900 dark:text-gray-100">{{ $t('reservationDetail.roomLabel') }} {{ reservation.data.room_assignment.room }}</span>
        {{ $t('reservationDetail.assignedAt') }} {{ formatDateTime(reservation.data.room_assignment.assigned_at) }}
      </div>

      <div class="rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ $t('reservationDetail.folioTitle') }}</h2>
          <div class="flex items-center gap-3">
            <a
              :href="`/printview?doctype=Reservation&name=${encodeURIComponent(props.id)}&format=Reservation Folio&no_letterhead=0`"
              target="_blank"
              rel="noopener"
              class="text-xs font-medium text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
            >
              {{ $t('reservationDetail.printInvoice') }}
            </a>
            <Button size="sm" variant="outline" @click="openPayment">{{ $t('reservationDetail.recordPaymentBtn') }}</Button>
          </div>
        </div>

        <div v-if="folio.loading && !folio.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>
        <template v-else-if="folio.data">
          <table class="min-w-full divide-y divide-gray-100 text-sm dark:divide-gray-800">
            <tbody class="divide-y divide-gray-50 dark:divide-gray-800/60">
              <tr v-for="line in folio.data.lines" :key="line.name">
                <td class="py-2 text-gray-700 dark:text-gray-300">
                  {{ statusLabel(line.type) }}
                  <span v-if="line.payment_method" class="text-gray-400"> · {{ statusLabel(line.payment_method) }}</span>
                </td>
                <td class="py-2 text-right text-gray-700 dark:text-gray-300">{{ formatMoney(line.amount_minor, line.currency) }}</td>
              </tr>
              <tr v-if="!folio.data.lines.length">
                <td colspan="2" class="py-2 text-gray-500 dark:text-gray-400">{{ $t('reservationDetail.noFolioLines') }}</td>
              </tr>
            </tbody>
          </table>
          <div class="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-800">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ $t('reservationDetail.balanceDue') }}</span>
            <span
              class="text-base font-bold"
              :class="folio.data.balance_due_minor > 0 ? 'text-amber-600' : 'text-green-600'"
            >
              {{ formatMoney(folio.data.balance_due_minor, folio.data.currency || reservation.data.currency) }}
            </span>
          </div>
        </template>
      </div>

      <div class="flex flex-wrap gap-2">
        <Button v-if="reservation.data.status === 'confirmed'" variant="solid" @click="openCheckIn">
          {{ $t('reservationDetail.checkInBtn') }}
        </Button>
        <Button v-if="reservation.data.status === 'checked_in'" variant="solid" :loading="checkOut.loading" @click="doCheckOut">
          {{ $t('reservationDetail.checkOutBtn') }}
        </Button>
        <Button v-if="reservation.data.status === 'confirmed'" variant="outline" theme="red" @click="cancelOpen = true">
          {{ $t('reservationDetail.cancelReservationBtn') }}
        </Button>
      </div>
    </template>

    <!-- Check-in: room picker -->
    <Dialog v-model="checkInOpen" :options="{ title: $t('reservationDetail.assignRoomDialogTitle') }">
      <template #body-content>
        <div v-if="availableRooms.loading" class="text-sm text-gray-500">{{ $t('reservationDetail.loadingRooms') }}</div>
        <div v-else-if="!availableRooms.data?.length" class="text-sm text-gray-500">
          {{ $t('reservationDetail.noReadyRoom') }}
        </div>
        <div v-else class="max-h-72 space-y-1 overflow-y-auto">
          <button
            v-for="r in availableRooms.data"
            :key="r.name"
            type="button"
            class="w-full rounded-md border px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
            :class="
              selectedRoom === r.name
                ? 'border-gray-900 dark:border-gray-100'
                : 'border-gray-200 dark:border-gray-700'
            "
            @click="selectedRoom = r.name"
          >
            {{ $t('reservationDetail.roomLabel') }} {{ r.room_number }} <span class="text-gray-400">· {{ $t('reservationDetail.floorLabel') }} {{ r.floor || '—' }}</span>
          </button>
        </div>
        <p v-if="checkIn.error" class="mt-3 text-sm text-red-600">{{ checkIn.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="checkInOpen = false">{{ $t('reservationDetail.cancelBtn') }}</Button>
          <Button variant="solid" :disabled="!selectedRoom" :loading="checkIn.loading" @click="doCheckIn">
            {{ $t('reservationDetail.confirmCheckin') }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- Cancel -->
    <Dialog v-model="cancelOpen" :options="{ title: $t('reservationDetail.cancelDialogTitle') }">
      <template #body-content>
        <textarea
          v-model="cancelReason"
          rows="3"
          :placeholder="$t('reservationDetail.reasonPlaceholder')"
          class="w-full rounded-md border-gray-200 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <p v-if="cancelResource.error" class="mt-2 text-sm text-red-600">{{ cancelResource.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="cancelOpen = false">{{ $t('reservationDetail.backBtn') }}</Button>
          <Button variant="solid" theme="red" :loading="cancelResource.loading" @click="doCancel">
            {{ $t('reservationDetail.confirmCancel') }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- Record payment -->
    <Dialog v-model="paymentOpen" :options="{ title: $t('reservationDetail.recordPaymentDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('reservationDetail.amountField')">
            <input v-model.number="paymentForm.amount" type="number" min="1" step="1" class="input-field" />
          </Field>
          <Field :label="$t('reservationDetail.methodField')">
            <select v-model="paymentForm.method" class="select-field w-full">
              <option v-for="m in PAYMENT_METHODS" :key="m" :value="m">{{ statusLabel(m) }}</option>
            </select>
          </Field>
        </div>
        <p v-if="recordPayment.error" class="mt-3 text-sm text-red-600">{{ recordPayment.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="paymentOpen = false">{{ $t('common.cancel') }}</Button>
          <Button variant="solid" :disabled="!paymentForm.amount" :loading="recordPayment.loading" @click="doRecordPayment">
            {{ $t('reservationDetail.recordPaymentBtn') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { RouterLink, useRouter } from 'vue-router'
import {
  availableRoomsResource,
  cancelReservationResource,
  checkInResource,
  checkOutResource,
  reservationResource,
} from '@/api/pms'
import { folioResource, recordPaymentResource } from '@/api/finance'
import { formatDate, formatDateTime, formatMoney, statusLabel } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import InfoRow from '@/components/InfoRow.vue'
import Field from '@/components/Field.vue'

const PAYMENT_METHODS = ['cash', 'mobile_money', 'bank_transfer', 'card', 'other']

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const reservation = reservationResource()
const availableRooms = availableRoomsResource()
const checkIn = checkInResource()
const checkOut = checkOutResource()
const cancelResource = cancelReservationResource()
const folio = folioResource()
const recordPayment = recordPaymentResource()

const checkInOpen = ref(false)
const cancelOpen = ref(false)
const paymentOpen = ref(false)
const selectedRoom = ref('')
const cancelReason = ref('')
const paymentForm = ref({ amount: null, method: 'cash' })

function load() {
  reservation.fetch({ name: props.id })
  loadFolio()
}

function loadFolio() {
  folio.fetch({ reservation: props.id })
}

onMounted(load)
watch(() => props.id, load)

function openPayment() {
  paymentForm.value = { amount: null, method: 'cash' }
  recordPayment.error = null
  paymentOpen.value = true
}

function doRecordPayment() {
  recordPayment.submit(
    {
      reservation: props.id,
      amount_minor: paymentForm.value.amount,
      currency: reservation.data?.currency,
      method: paymentForm.value.method,
    },
    {
      onSuccess() {
        paymentOpen.value = false
        loadFolio()
      },
    },
  )
}

function openCheckIn() {
  selectedRoom.value = ''
  checkIn.error = null
  checkInOpen.value = true
  availableRooms.fetch({ reservation: props.id })
}

function doCheckIn() {
  checkIn.submit(
    { reservation: props.id, room: selectedRoom.value },
    {
      onSuccess() {
        checkInOpen.value = false
        load()
      },
    },
  )
}

function doCheckOut() {
  checkOut.submit({ reservation: props.id }, { onSuccess: load })
}

function doCancel() {
  cancelResource.submit(
    { reservation: props.id, reason: cancelReason.value || undefined },
    {
      onSuccess() {
        cancelOpen.value = false
        load()
      },
    },
  )
}
</script>
