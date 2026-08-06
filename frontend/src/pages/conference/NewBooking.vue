<template>
  <div class="max-w-xl space-y-6">
    <RouterLink :to="{ name: 'ConferenceBookings' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      ← Back to conference &amp; events
    </RouterLink>

    <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">New Conference Booking</h1>

    <Card>
      <div class="space-y-3">
        <Field label="Space">
          <input v-model="form.space_name" type="text" placeholder="e.g. Grand Ballroom" class="input-field" />
        </Field>
        <Field label="Booked By">
          <input v-model="form.booked_by" type="text" placeholder="Guest or company name" class="input-field" />
        </Field>
        <div class="grid grid-cols-2 gap-3">
          <Field label="Start">
            <input v-model="form.start_at" type="datetime-local" class="input-field" />
          </Field>
          <Field label="End">
            <input v-model="form.end_at" type="datetime-local" class="input-field" />
          </Field>
        </div>
        <Field label="Catering notes (optional)">
          <textarea v-model="form.catering" rows="2" class="input-field" placeholder="e.g. Coffee service for 40 at 10am" />
        </Field>
      </div>
    </Card>

    <p v-if="createBooking.error" class="text-sm text-red-600">{{ createBooking.error.messages?.[0] }}</p>
    <Button variant="solid" :disabled="!canSubmit" :loading="createBooking.loading" @click="submit">
      Book Space
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
const form = reactive({ space_name: '', booked_by: '', start_at: '', end_at: '', catering: '' })

const canSubmit = computed(() => form.space_name && form.booked_by && form.start_at && form.end_at)

function submit() {
  createBooking.submit(
    {
      space_name: form.space_name,
      booked_by: form.booked_by,
      start_at: form.start_at.replace('T', ' '),
      end_at: form.end_at.replace('T', ' '),
      catering: form.catering ? JSON.stringify({ notes: form.catering }) : undefined,
    },
    { onSuccess: () => router.push({ name: 'ConferenceBookings' }) },
  )
}
</script>
