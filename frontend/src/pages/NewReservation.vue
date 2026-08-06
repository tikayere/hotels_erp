<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'Reservations' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      ← Back to reservations
    </RouterLink>
    <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">New Walk-in Reservation</h1>

    <form
      class="space-y-5 rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900"
      @submit.prevent="submit"
    >
      <div class="grid grid-cols-2 gap-4">
        <Field label="Property">
          <select v-model="form.property" :class="inputClass" @change="onPropertyChange">
            <option value="">Select property</option>
            <option v-for="p in boot.data?.properties || []" :key="p.name" :value="p.name">
              {{ p.property_name }}
            </option>
          </select>
        </Field>

        <Field label="Room Type">
          <select v-model="form.roomType" :class="inputClass" :disabled="!roomTypes.data?.length" @change="onRoomTypeChange">
            <option value="">Select room type</option>
            <option v-for="rt in roomTypes.data" :key="rt.name" :value="rt.name">{{ rt.room_type_name }}</option>
          </select>
        </Field>

        <Field label="Rate Plan">
          <select v-model="form.ratePlan" :class="inputClass" :disabled="!ratePlans.length" @change="onRatePlanOrDateChange">
            <option value="">Select rate plan</option>
            <option v-for="rp in ratePlans" :key="rp.name" :value="rp.name">{{ rp.plan_name }}</option>
          </select>
        </Field>

        <Field label="Rooms Requested">
          <input v-model.number="form.roomsRequested" type="number" min="1" :class="inputClass" />
        </Field>

        <Field label="Check-in">
          <input v-model="form.checkIn" type="date" :class="inputClass" @change="onRatePlanOrDateChange" />
        </Field>

        <Field label="Check-out">
          <input v-model="form.checkOut" type="date" :class="inputClass" @change="onRatePlanOrDateChange" />
        </Field>
      </div>

      <div v-if="availability.loading" class="text-sm text-gray-500 dark:text-gray-400">Checking availability…</div>
      <div v-else-if="availability.data" class="rounded-md bg-gray-50 p-3 text-sm dark:bg-gray-800">
        <p v-if="!enoughRooms" class="text-red-600">
          Only {{ availability.data.min_rooms_available }} room(s) available for the full stay.
        </p>
        <p v-else class="text-gray-700 dark:text-gray-300">
          {{ stayNights }} night(s) · Total {{ formatMoney(availability.data.total_amount_minor, availability.data.currency) }}
        </p>
      </div>

      <div>
        <div class="mb-2 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Guests</h2>
          <button type="button" class="text-xs font-medium text-gray-500 hover:text-gray-900 dark:hover:text-gray-100" @click="addGuest">
            + Add guest
          </button>
        </div>
        <div v-for="(g, i) in form.guests" :key="i" class="mb-2 grid grid-cols-4 gap-2">
          <input v-model="g.name" placeholder="Full name" required class="col-span-2" :class="inputClass" />
          <input v-model="g.phone" placeholder="Phone" :class="inputClass" />
          <div class="flex gap-1">
            <input v-model="g.email" placeholder="Email" :class="inputClass" />
            <button
              v-if="form.guests.length > 1"
              type="button"
              class="px-1 text-gray-400 hover:text-red-600"
              @click="form.guests.splice(i, 1)"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      <p v-if="create.error" class="text-sm text-red-600">{{ create.error.messages?.[0] || 'Could not create reservation' }}</p>

      <div class="flex justify-end gap-2">
        <Button variant="outline" type="button" @click="$router.back()">Cancel</Button>
        <Button variant="solid" type="submit" :loading="create.loading" :disabled="!canSubmit">
          Create Reservation
        </Button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, watch } from 'vue'
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { boot } from '@/session'
import { activeProperty } from '@/property'
import { availabilityResource, createWalkinReservationResource, roomTypesResource } from '@/api/pms'
import { formatMoney, nights } from '@/utils/format'
import Field from '@/components/Field.vue'

const inputClass =
  'w-full rounded-md border-gray-200 bg-white text-sm text-gray-700 focus:border-gray-400 focus:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200'

const router = useRouter()

const form = reactive({
  property: activeProperty.value || '',
  roomType: '',
  ratePlan: '',
  roomsRequested: 1,
  checkIn: '',
  checkOut: '',
  guests: [{ name: '', phone: '', email: '' }],
})

const roomTypes = roomTypesResource()
const availability = availabilityResource()
const create = createWalkinReservationResource()

const ratePlans = computed(() => roomTypes.data?.find((rt) => rt.name === form.roomType)?.rate_plans || [])
const stayNights = computed(() => nights(form.checkIn, form.checkOut))
const enoughRooms = computed(() => (availability.data?.min_rooms_available ?? 0) >= form.roomsRequested)

const canSubmit = computed(
  () =>
    form.roomType &&
    form.ratePlan &&
    form.checkIn &&
    form.checkOut &&
    stayNights.value > 0 &&
    form.roomsRequested >= 1 &&
    form.guests.some((g) => g.name.trim()) &&
    (!availability.data || enoughRooms.value),
)

onMounted(() => {
  if (!boot.fetched) boot.fetch()
  loadRoomTypes()
})
watch(() => form.property, loadRoomTypes)

function loadRoomTypes() {
  form.roomType = ''
  form.ratePlan = ''
  roomTypes.fetch({ property: form.property || undefined })
}

function onPropertyChange() {
  loadRoomTypes()
}

function onRoomTypeChange() {
  form.ratePlan = ''
  availability.data = null
}

function onRatePlanOrDateChange() {
  if (form.ratePlan && form.checkIn && form.checkOut && form.checkOut > form.checkIn) {
    availability.fetch({ rate_plan: form.ratePlan, check_in: form.checkIn, check_out: form.checkOut })
  } else {
    availability.data = null
  }
}

function addGuest() {
  form.guests.push({ name: '', phone: '', email: '' })
}

function submit() {
  const roomType = roomTypes.data?.find((rt) => rt.name === form.roomType)
  const ratePlan = ratePlans.value.find((rp) => rp.name === form.ratePlan)
  create.submit(
    {
      room_type_id: roomType?.code,
      rate_plan_code: ratePlan?.code,
      check_in: form.checkIn,
      check_out: form.checkOut,
      rooms_requested: form.roomsRequested,
      guests: form.guests
        .filter((g) => g.name.trim())
        .map((g) => ({ name: g.name, phone: g.phone || undefined, email: g.email || undefined })),
    },
    {
      onSuccess(data) {
        router.push({ name: 'ReservationDetail', params: { id: data.name } })
      },
    },
  )
}
</script>
