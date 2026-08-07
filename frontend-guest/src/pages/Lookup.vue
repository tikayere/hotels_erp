<template>
  <div class="mx-auto max-w-md px-4 py-16 sm:px-6">
    <h1 class="text-2xl font-semibold text-gray-900">{{ $t('lookup.title') }}</h1>
    <p class="mt-1 text-sm text-gray-600">
      {{ $t('lookup.subtitle') }}
    </p>

    <form class="mt-6 space-y-4" @submit.prevent="find">
      <label class="block text-sm">
        <span class="mb-1 block font-medium text-gray-700">{{ $t('lookup.confirmationNumber') }}</span>
        <input v-model="confirmationNumber" type="text" class="input-field w-full" placeholder="RES-00001" required />
      </label>
      <label class="block text-sm">
        <span class="mb-1 block font-medium text-gray-700">{{ $t('lookup.email') }}</span>
        <input v-model="email" type="email" class="input-field w-full" placeholder="jane@example.com" required />
      </label>
      <Button variant="solid" class="w-full !bg-gray-900" :loading="lookup.loading" type="submit">
        {{ $t('lookup.findBooking') }}
      </Button>
      <p v-if="lookup.error" class="text-sm text-red-600">
        {{ lookup.error.messages?.[0] || $t('lookup.notFound') }}
      </p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { getBookingResource } from '@/api/booking'
import { lastBooking } from '@/store'

const router = useRouter()
const confirmationNumber = ref('')
const email = ref('')
const lookup = getBookingResource()

function find() {
  lookup.fetch(
    { confirmation_number: confirmationNumber.value, email: email.value },
    {
      onSuccess(booking) {
        lastBooking.value = booking
        router.push({
          name: 'Confirmation',
          params: { confirmationNumber: booking.confirmation_number },
          query: { email: email.value },
        })
      },
    },
  )
}
</script>
