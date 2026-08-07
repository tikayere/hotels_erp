<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'RestaurantOrders' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('restaurantDetail.backLink') }}
    </RouterLink>

    <p v-if="order.error" class="text-sm text-red-600">{{ order.error.messages?.[0] || $t('restaurantDetail.failedToLoad') }}</p>
    <div v-if="order.loading && !order.data" class="text-sm text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>

    <template v-else-if="order.data">
      <div class="flex items-start justify-between rounded-lg border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ order.data.name }}</div>
          <div class="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {{ formatMoney(order.data.amount_minor, order.data.currency) }}
          </div>
        </div>
        <StatusBadge :status="order.data.status" />
      </div>

      <Card :title="$t('restaurantDetail.itemsTitle')">
        <ul class="divide-y divide-gray-50 text-sm dark:divide-gray-800/60">
          <li v-for="(l, i) in order.data.items" :key="i" class="flex items-center justify-between py-2">
            <span class="text-gray-700 dark:text-gray-300">{{ l.item }} × {{ l.qty }}</span>
            <span class="text-gray-500 dark:text-gray-400">{{ formatMoney((l.price_minor || 0) * (l.qty || 0), order.data.currency) }}</span>
          </li>
        </ul>
      </Card>

      <Card>
        <div class="grid grid-cols-2 gap-x-6 gap-y-4">
          <InfoRow :label="$t('restaurantDetail.reservationLabel')" :value="order.data.reservation" />
          <InfoRow :label="$t('restaurantDetail.assignedToLabel')" :value="order.data.assigned_to || $t('common.unassigned')" />
        </div>
      </Card>

      <div class="flex flex-wrap gap-2">
        <Button v-if="NEXT_STEP[order.data.status]" variant="solid" :loading="advance.loading" @click="doAdvance">
          {{ $t(NEXT_STEP[order.data.status]) }}
        </Button>
        <Button
          v-if="!['billed', 'cancelled'].includes(order.data.status)"
          variant="outline"
          theme="red"
          :loading="cancel.loading"
          @click="doCancel"
        >
          {{ $t('restaurantDetail.cancelOrder') }}
        </Button>
      </div>
      <p v-if="actionError" class="text-sm text-red-600">{{ actionError }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink } from 'vue-router'
import { advanceOrderResource, cancelOrderResource, orderResource } from '@/api/restaurant'
import { formatMoney } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import InfoRow from '@/components/InfoRow.vue'
import Card from '@/components/Card.vue'

const NEXT_STEP = {
  placed: 'restaurantDetail.sendToKitchen',
  in_kitchen: 'restaurantDetail.markServed',
  served: 'restaurantDetail.billOrder',
}

const props = defineProps({ id: { type: String, required: true } })

const order = orderResource()
const advance = advanceOrderResource()
const cancel = cancelOrderResource()

const actionError = computed(() => advance.error?.messages?.[0] || cancel.error?.messages?.[0])

function load() {
  order.fetch({ name: props.id })
}

onMounted(load)
watch(() => props.id, load)

function doAdvance() {
  advance.submit({ name: props.id }, { onSuccess: load })
}
function doCancel() {
  cancel.submit({ name: props.id }, { onSuccess: load })
}
</script>
