<template>
  <div class="mx-auto max-w-3xl px-4 py-12 sm:px-6">
    <h1 class="text-2xl font-semibold text-gray-900">{{ $t('book.title') }}</h1>
    <p class="mt-1 text-sm text-gray-600">{{ $t('book.subtitle') }}</p>

    <!-- Step 1: search -->
    <div class="mt-8 rounded-lg border border-gray-100 bg-white p-5 shadow-sm">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <label class="text-sm">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.checkIn') }}</span>
          <input v-model="checkIn" type="date" :min="today" class="input-field w-full" />
        </label>
        <label class="text-sm">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.checkOut') }}</span>
          <input v-model="checkOut" type="date" :min="checkIn || today" class="input-field w-full" />
        </label>
        <label class="text-sm">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.rooms') }}</span>
          <input v-model.number="roomsRequested" type="number" min="1" max="10" class="input-field w-full" />
        </label>
        <div class="flex items-end">
          <Button variant="solid" class="w-full !bg-gray-900" :loading="availability.loading" @click="search">
            {{ $t('book.search') }}
          </Button>
        </div>
      </div>
      <p v-if="searchError" class="mt-3 text-sm text-red-600">{{ searchError }}</p>
    </div>

    <!-- Results -->
    <div v-if="availability.data" class="mt-8">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
        {{ availability.data.length }} {{ $t('book.optionsFor', { nights }) }}
      </h2>

      <p v-if="!availability.data.length" class="mt-3 text-sm text-gray-500">
        {{ $t('book.noRoomsForDates') }}
      </p>

      <div class="mt-4 space-y-3">
        <button
          v-for="offer in availability.data"
          :key="offer.room_type_code + offer.rate_plan_code"
          type="button"
          class="flex w-full items-center justify-between gap-4 rounded-lg border p-4 text-left transition"
          :class="
            isSelected(offer)
              ? 'border-gray-900 ring-1 ring-gray-900'
              : 'border-gray-100 hover:border-gray-300'
          "
          @click="selectedOffer = offer"
        >
          <div>
            <div class="font-semibold text-gray-900">{{ offer.room_type_name }} — {{ offer.rate_plan_name }}</div>
            <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
              <span>👤 {{ $t('book.upToAdults', { n: offer.max_occupancy_adults }) }}</span>
              <span>{{ offer.refundable ? $t('book.freeCancellation') : $t('book.nonRefundable') }}</span>
              <span v-if="offer.includes_breakfast">{{ $t('book.breakfastIncluded') }}</span>
              <span>{{ $t('book.roomsLeft', { n: offer.rooms_available }) }}</span>
            </div>
          </div>
          <div class="shrink-0 text-right">
            <div class="text-lg font-semibold text-gray-900">
              {{ formatMoney(offer.total_amount_minor, offer.currency) }}
            </div>
            <div class="text-xs text-gray-500">{{ $t('book.totalForNights', { n: offer.nights }) }}</div>
          </div>
        </button>
      </div>
    </div>

    <!-- Step 2: guest details -->
    <div v-if="selectedOffer" class="mt-8 rounded-lg border border-gray-100 bg-white p-5 shadow-sm">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">{{ $t('book.yourDetails') }}</h2>

      <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label class="text-sm">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.fullName') }}</span>
          <input v-model="primaryGuest.name" type="text" class="input-field w-full" placeholder="Jane Doe" />
        </label>
        <label class="text-sm">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.email') }}</span>
          <input v-model="primaryGuest.email" type="email" class="input-field w-full" placeholder="jane@example.com" />
        </label>
        <label class="text-sm sm:col-span-2">
          <span class="mb-1 block font-medium text-gray-700">{{ $t('book.phone') }}</span>
          <input v-model="primaryGuest.phone" type="tel" class="input-field w-full" placeholder="+1 555 000 0000" />
        </label>
      </div>

      <div v-if="additionalGuests.length" class="mt-4 space-y-2">
        <div v-for="(g, i) in additionalGuests" :key="i" class="flex items-center gap-2">
          <input v-model="g.name" type="text" class="input-field flex-1" :placeholder="$t('book.guestNamePlaceholder', { n: i + 2 })" />
          <button type="button" class="text-gray-400 hover:text-red-600" @click="additionalGuests.splice(i, 1)">✕</button>
        </div>
      </div>
      <button type="button" class="mt-3 text-xs font-medium text-gray-500 hover:text-gray-900" @click="additionalGuests.push({ name: '' })">
        {{ $t('book.addAnotherGuest') }}
      </button>

      <div class="mt-6 flex items-center justify-between border-t border-gray-100 pt-4">
        <div>
          <div class="text-xs text-gray-500">{{ $t('book.totalDueAtHotel') }}</div>
          <div class="text-lg font-semibold text-gray-900">
            {{ formatMoney(selectedOffer.total_amount_minor, selectedOffer.currency) }}
          </div>
        </div>
        <Button variant="solid" class="!bg-gray-900" :disabled="!canSubmit" :loading="createBooking.loading" @click="submit">
          {{ $t('book.confirmBooking') }}
        </Button>
      </div>
      <p v-if="createBooking.error" class="mt-3 text-sm text-red-600">
        {{ createBooking.error.messages?.[0] || $t('book.genericError') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Button } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { availabilityResource, createBookingResource } from '@/api/booking'
import { formatMoney, lastBooking, nightsBetween } from '@/store'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const today = new Date().toISOString().slice(0, 10)
const checkIn = ref('')
const checkOut = ref('')
const roomsRequested = ref(1)
const presetRoomCode = ref(route.query.room || '')

const availability = availabilityResource()
const createBooking = createBookingResource()
const selectedOffer = ref(null)
const searchError = ref('')

const primaryGuest = reactive({ name: '', email: '', phone: '' })
const additionalGuests = reactive([])

const nights = computed(() => nightsBetween(checkIn.value, checkOut.value))

function isSelected(offer) {
  return (
    selectedOffer.value &&
    selectedOffer.value.room_type_code === offer.room_type_code &&
    selectedOffer.value.rate_plan_code === offer.rate_plan_code
  )
}

function search() {
  searchError.value = ''
  if (!checkIn.value || !checkOut.value) {
    searchError.value = t('book.errChooseDates')
    return
  }
  if (checkOut.value <= checkIn.value) {
    searchError.value = t('book.errCheckoutAfterCheckin')
    return
  }
  selectedOffer.value = null
  availability.fetch({
    check_in: checkIn.value,
    check_out: checkOut.value,
    room_type_code: presetRoomCode.value || undefined,
  })
}

const canSubmit = computed(() => selectedOffer.value && primaryGuest.name.trim() && primaryGuest.email.trim())

function submit() {
  const guests = [
    { name: primaryGuest.name, email: primaryGuest.email, phone: primaryGuest.phone || undefined },
    ...additionalGuests.filter((g) => g.name?.trim()).map((g) => ({ name: g.name })),
  ]
  createBooking.submit(
    {
      room_type_code: selectedOffer.value.room_type_code,
      rate_plan_code: selectedOffer.value.rate_plan_code,
      check_in: checkIn.value,
      check_out: checkOut.value,
      rooms_requested: roomsRequested.value,
      guests: JSON.stringify(guests),
    },
    {
      onSuccess(booking) {
        lastBooking.value = booking
        router.push({
          name: 'Confirmation',
          params: { confirmationNumber: booking.confirmation_number },
          query: { email: booking.guests?.[0]?.email || primaryGuest.email },
        })
      },
    },
  )
}

onMounted(() => {
  // A default 1-night stay starting today makes the search results appear
  // immediately when arriving from a "Book This Room" link, instead of
  // showing an empty form the guest has to fill in from scratch.
  if (presetRoomCode.value) {
    checkIn.value = today
    const d = new Date()
    d.setDate(d.getDate() + 1)
    checkOut.value = d.toISOString().slice(0, 10)
    search()
  }
})
</script>
