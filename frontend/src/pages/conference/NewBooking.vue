<template>
  <div class="max-w-xl space-y-6">
    <RouterLink :to="{ name: 'ConferenceBookings' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('conferenceNew.backLink') }}
    </RouterLink>

    <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('conferenceNew.title') }}</h1>

    <Card>
      <div class="space-y-3">
        <Field :label="$t('conferenceNew.spaceField')">
          <input v-model="form.space_name" type="text" :placeholder="$t('conferenceNew.spacePlaceholder')" class="input-field" />
        </Field>
        <Field :label="$t('conferenceNew.bookedByField')">
          <input v-model="form.booked_by" type="text" :placeholder="$t('conferenceNew.bookedByPlaceholder')" class="input-field" />
        </Field>
        <div class="grid grid-cols-2 gap-3">
          <Field :label="$t('conferenceNew.startField')">
            <input v-model="form.start_at" type="datetime-local" class="input-field" />
          </Field>
          <Field :label="$t('conferenceNew.endField')">
            <input v-model="form.end_at" type="datetime-local" class="input-field" />
          </Field>
        </div>
        <Field :label="$t('conferenceNew.cateringOptionalField')">
          <textarea v-model="form.catering" rows="2" class="input-field" :placeholder="$t('conferenceNew.cateringPlaceholder')" />
        </Field>
        <div class="grid grid-cols-2 gap-3">
          <Field :label="$t('conferenceNew.amountField')">
            <input v-model.number="form.total_amount_minor" type="number" min="0" class="input-field" />
          </Field>
          <Field :label="$t('conferenceNew.currencyField')">
            <input v-model="form.currency" type="text" placeholder="USD" class="input-field" />
          </Field>
        </div>
      </div>
    </Card>

    <p v-if="createBooking.error" class="text-sm text-red-600">{{ createBooking.error.messages?.[0] }}</p>
    <Button variant="solid" :disabled="!canSubmit" :loading="createBooking.loading" @click="submit">
      {{ $t('conferenceNew.bookSpace') }}
    </Button>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink, useRouter } from 'vue-router'
import { createBookingResource } from '@/api/conference'
import Field from '@/components/Field.vue'
import Card from '@/components/Card.vue'

const router = useRouter()
const createBooking = createBookingResource()
const form = reactive({ space_name: '', booked_by: '', start_at: '', end_at: '', catering: '', total_amount_minor: null, currency: '' })

const canSubmit = computed(() => form.space_name && form.booked_by && form.start_at && form.end_at)

function submit() {
  createBooking.submit(
    {
      space_name: form.space_name,
      booked_by: form.booked_by,
      start_at: form.start_at.replace('T', ' '),
      end_at: form.end_at.replace('T', ' '),
      catering: form.catering ? JSON.stringify({ notes: form.catering }) : undefined,
      total_amount_minor: form.total_amount_minor || undefined,
      currency: form.total_amount_minor ? form.currency : undefined,
    },
    { onSuccess: () => router.push({ name: 'ConferenceBookings' }) },
  )
}
</script>
