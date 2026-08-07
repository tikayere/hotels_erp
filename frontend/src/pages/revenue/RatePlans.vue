<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('revenue.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="roomTypeFilter" class="select-field">
          <option value="">{{ $t('revenue.allRoomTypes') }}</option>
          <option v-for="rt in roomTypes.data" :key="rt.name" :value="rt.name">{{ rt.room_type_name }}</option>
        </select>
        <Button variant="solid" @click="openNewPlan">{{ $t('revenue.newRatePlan') }}</Button>
      </div>
    </div>

    <p v-if="plans.error" class="text-sm text-red-600">{{ plans.error.messages?.[0] || $t('common.failedToLoad') }}</p>
    <div class="overflow-x-auto rounded-lg border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-900">
      <table class="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
        <thead>
          <tr class="text-left text-xs font-medium text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3">{{ $t('revenue.planCol') }}</th>
            <th class="px-4 py-3">{{ $t('revenue.roomTypeCol') }}</th>
            <th class="px-4 py-3 text-right">{{ $t('revenue.basePriceCol') }}</th>
            <th class="px-4 py-3">{{ $t('revenue.rulesCol') }}</th>
            <th class="px-4 py-3">{{ $t('revenue.activeCol') }}</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <tr v-if="plans.loading && !plans.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!plans.data?.length">
            <td class="px-4 py-6 text-gray-500 dark:text-gray-400" colspan="6">{{ $t('revenue.noneMatch') }}</td>
          </tr>
          <tr
            v-for="p in plans.data"
            :key="p.name"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60"
            @click="$router.push({ name: 'RatePlanDetail', params: { id: p.name } })"
          >
            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
              {{ p.plan_name }}
              <span class="ml-1 text-xs text-gray-400">{{ p.code }}</span>
            </td>
            <td class="px-4 py-3 text-gray-700 dark:text-gray-300">{{ p.room_type_name }}</td>
            <td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{{ p.base_price_minor ?? '—' }}</td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">
              {{ p.active_rule_count ? $t('revenue.ruleCount', { n: p.active_rule_count }) : $t('revenue.noRules') }}
            </td>
            <td class="px-4 py-3">
              <span v-if="p.active" class="text-xs font-medium text-green-600 dark:text-green-400">{{ $t('status.active') }}</span>
              <span v-else class="text-xs text-gray-400">{{ $t('revenue.inactive') }}</span>
            </td>
            <td class="px-4 py-3 text-right text-gray-400">›</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="dialogOpen" :options="{ title: $t('revenue.newRatePlanDialogTitle') }">
      <template #body-content>
        <div class="space-y-3">
          <Field :label="$t('revenue.roomTypeField')">
            <select v-model="form.room_type" class="select-field w-full">
              <option v-for="rt in roomTypes.data" :key="rt.name" :value="rt.name">{{ rt.room_type_name }}</option>
            </select>
          </Field>
          <div class="grid grid-cols-2 gap-3">
            <Field :label="$t('revenue.codeField')">
              <input v-model="form.code" type="text" placeholder="FLEX" class="input-field" />
            </Field>
            <Field :label="$t('revenue.planNameField')">
              <input v-model="form.plan_name" type="text" class="input-field" />
            </Field>
          </div>
          <Field :label="$t('revenue.basePriceField')">
            <input v-model.number="form.base_price_minor" type="number" min="0" class="input-field" />
          </Field>
          <div class="flex items-center gap-4">
            <label class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
              <input v-model="form.refundable" type="checkbox" class="rounded border-gray-300" />
              {{ $t('revenue.refundableField') }}
            </label>
            <label class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
              <input v-model="form.includes_breakfast" type="checkbox" class="rounded border-gray-300" />
              {{ $t('revenue.includesBreakfastField') }}
            </label>
          </div>
        </div>
        <p v-if="createPlan.error" class="mt-3 text-sm text-red-600">{{ createPlan.error.messages?.[0] }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" @click="dialogOpen = false">{{ $t('common.cancel') }}</Button>
          <Button
            variant="solid"
            :disabled="!form.room_type || !form.code || !form.plan_name"
            :loading="createPlan.loading"
            @click="submitPlan"
          >
            {{ $t('revenue.createBtn') }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { createRatePlanResource, ratePlansResource } from '@/api/revenue'
import { roomTypesResource } from '@/api/pms'
import Field from '@/components/Field.vue'

const roomTypeFilter = ref('')
const plans = ratePlansResource()
const roomTypes = roomTypesResource()
const createPlan = createRatePlanResource()

function load() {
  plans.fetch({ room_type: roomTypeFilter.value || undefined })
}
onMounted(() => {
  load()
  roomTypes.fetch({})
})
watch(roomTypeFilter, load)

const dialogOpen = ref(false)
const form = reactive({ room_type: '', code: '', plan_name: '', base_price_minor: null, refundable: true, includes_breakfast: false })
function openNewPlan() {
  Object.assign(form, { room_type: roomTypes.data?.[0]?.name || '', code: '', plan_name: '', base_price_minor: null, refundable: true, includes_breakfast: false })
  createPlan.error = null
  dialogOpen.value = true
}
function submitPlan() {
  createPlan.submit(
    {
      room_type: form.room_type,
      code: form.code,
      plan_name: form.plan_name,
      base_price_minor: form.base_price_minor || undefined,
      refundable: form.refundable ? 1 : 0,
      includes_breakfast: form.includes_breakfast ? 1 : 0,
    },
    { onSuccess: (p) => { dialogOpen.value = false; load() } },
  )
}
</script>
