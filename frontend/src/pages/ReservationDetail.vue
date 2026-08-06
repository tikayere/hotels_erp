<template>
  <div class="max-w-3xl space-y-6">
    <RouterLink :to="{ name: 'Reservations' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      ← Back to reservations
    </RouterLink>

    <p v-if="reservation.error" class="text-sm text-red-600">
      {{ reservation.error.messages?.[0] || 'Failed to load this reservation' }}
    </p>
    <div v-if="reservation.loading && !reservation.data" class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>

    <template v-else-if="reservation.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">Confirmation #</div>
          <div class="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {{ reservation.data.confirmation_number }}
          </div>
        </div>
        <StatusBadge :status="reservation.data.status" />
      </div>

      <div class="grid grid-cols-2 gap-x-6 gap-y-4 rounded-lg border border-gray-100 bg-white p-5 sm:grid-cols-3 dark:border-gray-800 dark:bg-gray-900">
        <InfoRow label="Room Type" :value="reservation.data.room_type?.room_type_name" />
        <InfoRow label="Rate Plan" :value="reservation.data.rate_plan?.plan_name" />
        <InfoRow label="Rooms" :value="reservation.data.rooms_requested" />
        <InfoRow label="Check-in" :value="formatDate(reservation.data.check_in)" />
        <InfoRow label="Check-out" :value="formatDate(reservation.data.check_out)" />
        <InfoRow
          label="Total"
          :value="formatMoney(reservation.data.total_amount_minor, reservation.data.currency)"
        />
        <InfoRow v-if="reservation.data.payment_reference" label="Payment Ref" :value="reservation.data.payment_reference" />
        <InfoRow label="Booked" :value="formatDateTime(reservation.data.created_at)" />
      </div>

      <div class="rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <h2 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Guests</h2>
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
        <span class="font-medium text-gray-900 dark:text-gray-100">Room {{ reservation.data.room_assignment.room }}</span>
        assigned {{ formatDateTime(reservation.data.room_assignment.assigned_at) }}
      </div>

      <div class="flex flex-wrap gap-2">
        <Button v-if="reservation.data.status === 'confirmed'" variant="solid" @click="openCheckIn">
          Check In
        </Button>
        <Button v-if="reservation.data.status === 'checked_in'" variant="solid" :loading="checkOut.loading" @click="doCheckOut">
          Check Out
        </Button>
        <Button v-if="reservation.data.status === 'confirmed'" variant="outline" theme="red" @click="cancelOpen = true">
          Cancel Reservation
        </Button>
      </div>
    </template>

    <!-- Check-in: room picker -->
    <Dialog v-model="checkInOpen" :options="{ title: 'Assign a Room' }">
      <template #body-content>
        <div v-if="availableRooms.loading" class="text-sm text-gray-500">Loading rooms…</div>
        <div v-else-if="!availableRooms.data?.length" class="text-sm text-gray-500">
          No ready room of this type right now — check the room board.
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
            Room {{ r.room_number }} <span class="text-gray-400">· Floor {{ r.floor || '—' }}</span>
          </button>
        </div>
        <p v-if="checkIn.error" class="mt-3 text-sm text-red-600">{{ checkIn.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="checkInOpen = false">Cancel</Button>
          <Button variant="solid" :disabled="!selectedRoom" :loading="checkIn.loading" @click="doCheckIn">
            Confirm Check-in
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- Cancel -->
    <Dialog v-model="cancelOpen" :options="{ title: 'Cancel Reservation' }">
      <template #body-content>
        <textarea
          v-model="cancelReason"
          rows="3"
          placeholder="Reason (optional)"
          class="w-full rounded-md border-gray-200 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <p v-if="cancelResource.error" class="mt-2 text-sm text-red-600">{{ cancelResource.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="cancelOpen = false">Back</Button>
          <Button variant="solid" theme="red" :loading="cancelResource.loading" @click="doCancel">
            Confirm Cancel
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
import { formatDate, formatDateTime, formatMoney } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import InfoRow from '@/components/InfoRow.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const reservation = reservationResource()
const availableRooms = availableRoomsResource()
const checkIn = checkInResource()
const checkOut = checkOutResource()
const cancelResource = cancelReservationResource()

const checkInOpen = ref(false)
const cancelOpen = ref(false)
const selectedRoom = ref('')
const cancelReason = ref('')

function load() {
  reservation.fetch({ name: props.id })
}

onMounted(load)
watch(() => props.id, load)

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
