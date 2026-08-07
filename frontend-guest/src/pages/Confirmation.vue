<template>
  <div class="mx-auto max-w-3xl px-4 py-12 sm:px-6">
    <div v-if="!booking && lookup.loading" class="text-center text-sm text-gray-500">{{ $t('confirmation.loading') }}</div>

    <div v-else-if="!booking" class="text-center">
      <div class="text-4xl">🔍</div>
      <h1 class="mt-3 text-lg font-semibold text-gray-900">{{ $t('confirmation.notFoundTitle') }}</h1>
      <p class="mt-1 text-sm text-gray-600">{{ $t('confirmation.notFoundSubtitle') }}</p>
      <RouterLink :to="{ name: 'Lookup' }" class="btn-secondary mt-6 inline-flex">{{ $t('confirmation.lookUpMyBooking') }}</RouterLink>
    </div>

    <template v-else>
      <div class="text-center">
        <div class="text-4xl">🎉</div>
        <h1 class="mt-2 text-2xl font-semibold text-gray-900">{{ $t('confirmation.confirmedTitle') }}</h1>
        <p class="mt-1 text-sm text-gray-600">
          {{ $t('confirmation.confirmedSubtitle') }}
        </p>
      </div>

      <div class="mt-8">
        <TicketCard ref="ticketRef" :booking="booking" :property="property" />
      </div>

      <div class="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button variant="solid" class="!bg-gray-900" :loading="downloading" @click="downloadTicket">
          {{ $t('confirmation.downloadTicket') }}
        </Button>
        <RouterLink :to="{ name: 'Rooms' }" class="btn-secondary">{{ $t('confirmation.bookAnotherStay') }}</RouterLink>
      </div>
      <p v-if="downloadError" class="mt-3 text-center text-sm text-red-600">{{ downloadError }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'
import TicketCard from '@/components/TicketCard.vue'
import { getBookingResource } from '@/api/booking'
import { lastBooking, portalSettings } from '@/store'

const props = defineProps({
  confirmationNumber: { type: String, required: true },
})
const route = useRoute()
const { t } = useI18n()

const lookup = getBookingResource()
const booking = ref(null)
const ticketRef = ref(null)
const downloading = ref(false)
const downloadError = ref('')

const property = computed(() => booking.value?.property || portalSettings.value?.property)

onMounted(async () => {
  // Cheapest path: the booking we just created is still in memory (came
  // straight from Book.vue in the same tab). Otherwise (bookmarked link,
  // page refresh, QR scan on a fresh tab) fall back to the same
  // confirmation-number + email lookup Lookup.vue uses.
  if (lastBooking.value && lastBooking.value.confirmation_number === props.confirmationNumber) {
    booking.value = lastBooking.value
    return
  }
  const email = route.query.email
  if (!email) return
  await lookup.fetch({ confirmation_number: props.confirmationNumber, email })
  if (lookup.data) booking.value = lookup.data
})

async function downloadTicket() {
  downloadError.value = ''
  const node = ticketRef.value?.rootEl
  if (!node) return
  downloading.value = true
  try {
    const canvas = await html2canvas(node, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' })
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 40
    const imgWidth = pageWidth - margin * 2
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, Math.min(imgHeight, pageHeight - margin * 2))
    pdf.save(`booking-${booking.value.confirmation_number}.pdf`)
  } catch (e) {
    downloadError.value = t('confirmation.downloadError')
  } finally {
    downloading.value = false
  }
}
</script>
