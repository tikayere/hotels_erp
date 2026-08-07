<template>
  <div class="max-w-2xl space-y-6">
    <RouterLink :to="{ name: 'RestaurantOrders' }" class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
      {{ $t('restaurantNew.backLink') }}
    </RouterLink>

    <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('restaurantNew.title') }}</h1>

    <Card>
      <div class="grid grid-cols-2 gap-4">
        <Field :label="$t('restaurantNew.reservationOptionalField')">
          <input v-model="reservation" type="text" placeholder="RES-00001" class="input-field" />
        </Field>
        <Field :label="$t('restaurantNew.currencyField')">
          <input v-model="currency" type="text" placeholder="USD" class="input-field" />
        </Field>
      </div>
    </Card>

    <Card :title="$t('restaurantNew.itemsTitle')">
      <template #actions>
        <Button variant="outline" @click="addLine">{{ $t('restaurantNew.addLine') }}</Button>
      </template>
      <div class="space-y-2">
        <div v-for="(line, i) in lines" :key="i" class="grid grid-cols-12 items-center gap-2">
          <input v-model="line.item" type="text" :placeholder="$t('restaurantNew.itemPlaceholder')" class="input-field col-span-6" />
          <input v-model.number="line.qty" type="number" min="1" :placeholder="$t('restaurantNew.qtyPlaceholder')" class="input-field col-span-2" />
          <input v-model.number="line.price_minor" type="number" min="0" :placeholder="$t('restaurantNew.pricePlaceholder')" class="input-field col-span-3" />
          <button type="button" class="col-span-1 text-gray-400 hover:text-red-600" @click="lines.splice(i, 1)">✕</button>
        </div>
      </div>
      <div class="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-sm dark:border-gray-800">
        <span class="text-gray-500 dark:text-gray-400">{{ $t('restaurantNew.totalLabel') }}</span>
        <span class="font-semibold text-gray-900 dark:text-gray-100">{{ formatMoney(totalMinor, currency) }}</span>
      </div>
    </Card>

    <p v-if="createOrder.error" class="text-sm text-red-600">{{ createOrder.error.messages?.[0] }}</p>
    <Button variant="solid" :disabled="!canSubmit" :loading="createOrder.loading" @click="submit">
      {{ $t('restaurantNew.placeOrder') }}
    </Button>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Button } from 'frappe-ui'
import { RouterLink, useRouter } from 'vue-router'
import { createOrderResource } from '@/api/restaurant'
import { formatMoney } from '@/utils/format'
import Field from '@/components/Field.vue'
import Card from '@/components/Card.vue'

const router = useRouter()
const reservation = ref('')
const currency = ref('USD')
const lines = reactive([{ item: '', qty: 1, price_minor: 0 }])
const createOrder = createOrderResource()

function addLine() {
  lines.push({ item: '', qty: 1, price_minor: 0 })
}

const totalMinor = computed(() =>
  lines.reduce((sum, l) => sum + (Number(l.qty) || 0) * (Number(l.price_minor) || 0), 0),
)

const canSubmit = computed(
  () => currency.value && lines.some((l) => l.item && Number(l.qty) > 0) && totalMinor.value > 0,
)

function submit() {
  const items = lines.filter((l) => l.item && Number(l.qty) > 0)
  createOrder.submit(
    {
      items: JSON.stringify(items),
      amount_minor: totalMinor.value,
      currency: currency.value,
      reservation: reservation.value || undefined,
    },
    {
      onSuccess(order) {
        router.push({ name: 'RestaurantOrderDetail', params: { id: order.name } })
      },
    },
  )
}
</script>
