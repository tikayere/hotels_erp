<template>
  <div ref="rootEl" class="mx-auto max-w-xl overflow-hidden rounded-xl border border-gray-200 bg-white">
    <!-- Header / letterhead -->
    <div class="flex items-center justify-between gap-4 bg-gray-900 px-6 py-5 text-white">
      <div class="flex items-center gap-3">
        <img v-if="property?.logo" :src="property.logo" alt="" class="h-10 w-10 rounded bg-white object-cover" />
        <span v-else class="text-3xl">🏨</span>
        <div>
          <div class="text-lg font-semibold leading-tight">{{ property?.property_name || $t('common.hotelFallback') }}</div>
          <div v-if="addressLine" class="text-xs text-gray-300">{{ addressLine }}</div>
        </div>
      </div>
      <div class="text-right">
        <div class="text-[10px] uppercase tracking-wider text-gray-300">{{ $t('ticket.bookingTicket') }}</div>
        <div class="text-sm font-semibold">{{ booking.status }}</div>
      </div>
    </div>

    <!-- Confirmation number + QR -->
    <div class="flex items-center justify-between gap-4 border-b border-dashed border-gray-300 px-6 py-5">
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.confirmationNumber') }}</div>
        <div class="font-mono text-2xl font-bold tracking-widest text-gray-900">{{ booking.confirmation_number }}</div>
      </div>
      <img v-if="qrDataUrl" :src="qrDataUrl" alt="Booking QR code" class="h-20 w-20 shrink-0" />
    </div>

    <!-- Stay details -->
    <div class="grid grid-cols-2 gap-4 px-6 py-5 text-sm">
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.checkIn') }}</div>
        <div class="font-semibold text-gray-900">{{ formatDate(booking.check_in) }}</div>
      </div>
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.checkOut') }}</div>
        <div class="font-semibold text-gray-900">{{ formatDate(booking.check_out) }}</div>
      </div>
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.room') }}</div>
        <div class="font-semibold text-gray-900">{{ booking.room_type_name }}</div>
        <div class="text-xs text-gray-500">{{ booking.rate_plan_name }}</div>
      </div>
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.rooms') }}</div>
        <div class="font-semibold text-gray-900">{{ booking.rooms_requested }}</div>
      </div>
      <div class="col-span-2">
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.guests') }}</div>
        <div class="font-semibold text-gray-900">{{ guestNames }}</div>
      </div>
    </div>

    <!-- Total -->
    <div class="flex items-center justify-between border-t border-dashed border-gray-300 px-6 py-5">
      <div>
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.payment') }}</div>
        <div class="text-sm font-semibold text-gray-900">{{ booking.payment_reference || $t('ticket.payAtHotel') }}</div>
      </div>
      <div class="text-right">
        <div class="text-xs uppercase tracking-wide text-gray-500">{{ $t('ticket.total') }}</div>
        <div class="text-xl font-bold text-gray-900">{{ formatMoney(booking.total_amount_minor, booking.currency) }}</div>
      </div>
    </div>

    <div class="bg-gray-50 px-6 py-3 text-center text-[11px] text-gray-500">
      {{ $t('ticket.footerNote') }}
      <span v-if="property?.phone"> {{ $t('ticket.questionsCall', { phone: property.phone }) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import { formatDate, formatMoney } from '@/store'

const props = defineProps({
  booking: { type: Object, required: true },
  property: { type: Object, default: null },
})

const rootEl = ref(null)
defineExpose({ rootEl })

const addressLine = computed(() => {
  const p = props.property
  if (!p) return ''
  return [p.address, p.city, p.country].filter(Boolean).join(', ')
})

const guestNames = computed(() => (props.booking.guests || []).map((g) => g.name).join(', '))

const qrDataUrl = ref('')

async function renderQr() {
  // Encodes a deep link straight back to this ticket (confirmation number +
  // the primary guest's email, the same two things get_booking() requires)
  // so scanning it at the front desk pulls the booking up immediately.
  const primaryEmail = props.booking.guests?.[0]?.email || ''
  const url = `${window.location.origin}/book/confirmation/${encodeURIComponent(
    props.booking.confirmation_number
  )}?email=${encodeURIComponent(primaryEmail)}`
  qrDataUrl.value = await QRCode.toDataURL(url, { margin: 1, width: 160 })
}

onMounted(renderQr)
watch(() => props.booking?.confirmation_number, renderQr)
</script>
