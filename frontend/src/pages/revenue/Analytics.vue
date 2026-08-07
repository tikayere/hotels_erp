<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ $t('analytics.title') }}</h1>
      <select v-model.number="windowDays" class="select-field">
        <option :value="7">{{ $t('analytics.last7') }}</option>
        <option :value="30">{{ $t('analytics.last30') }}</option>
        <option :value="90">{{ $t('analytics.last90') }}</option>
      </select>
    </div>

    <p v-if="kpis.error" class="text-sm text-red-600">{{ kpis.error.messages?.[0] || $t('common.failedToLoad') }}</p>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <KpiCard :label="$t('analytics.occupancyToday')" icon="🛏️" :value="kpis.data ? `${kpis.data.occupancy_percent_today}%` : null" />
      <KpiCard :label="$t('analytics.avgAdr30d')" icon="💵" :value="kpis.data ? formatMoney(kpis.data.avg_adr_minor_30d, kpis.data.currency) : null" />
      <KpiCard :label="$t('analytics.avgRevpar30d')" icon="📈" :value="kpis.data ? formatMoney(kpis.data.avg_revpar_minor_30d, kpis.data.currency) : null" />
      <KpiCard :label="$t('analytics.mtdRevenue')" icon="💰" :value="kpis.data ? formatMoney(kpis.data.mtd_revenue_minor, kpis.data.currency) : null" />
    </div>

    <Card :title="$t('analytics.occupancyTrendTitle')">
      <div v-if="!occupancy.data?.length" class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {{ occupancy.loading ? $t('common.loading') : $t('analytics.noData') }}
      </div>
      <AxisChart v-else :config="occupancyChartConfig" />
    </Card>

    <Card :title="$t('analytics.revenueTrendTitle')">
      <div v-if="!revenue.data?.length" class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {{ revenue.loading ? $t('common.loading') : $t('analytics.noData') }}
      </div>
      <AxisChart v-else :config="revenueChartConfig" />
    </Card>

    <Card :title="$t('analytics.adrRevparTrendTitle')">
      <div v-if="!adrRevpar.data?.length" class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {{ adrRevpar.loading ? $t('common.loading') : $t('analytics.noData') }}
      </div>
      <AxisChart v-else :config="adrRevparChartConfig" />
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { AxisChart } from 'frappe-ui'
import { adrRevparTrendResource, kpiSummaryResource, occupancyTrendResource, revenueTrendResource } from '@/api/analytics'
import { activeProperty } from '@/property'
import { formatMoney } from '@/utils/format'
import { useI18n } from 'vue-i18n'
import Card from '@/components/Card.vue'
import KpiCard from '@/components/KpiCard.vue'

const { t } = useI18n()
const windowDays = ref(30)

const kpis = kpiSummaryResource()
const occupancy = occupancyTrendResource()
const revenue = revenueTrendResource()
const adrRevpar = adrRevparTrendResource()

function load() {
  const property = activeProperty.value || undefined
  kpis.fetch({ property })
  occupancy.fetch({ property, days: windowDays.value })
  revenue.fetch({ property, days: windowDays.value })
  adrRevpar.fetch({ property, days: windowDays.value })
}
onMounted(load)
watch([windowDays, activeProperty], load)

// AxisChart (frappe-ui, eCharts-backed) reads each series value off
// `row[series[i].name]` (see node_modules/frappe-ui's axisChartOptions.ts)
// -- `name` here doubles as both the display label and the data key, so it
// must match the field name in `data` exactly.
const occupancyChartConfig = computed(() => ({
  title: t('analytics.occupancyTrendTitle'),
  data: occupancy.data || [],
  xAxis: { key: 'date', type: 'time' },
  yAxis: { title: '%', yMin: 0 },
  series: [{ name: 'occupancy_percent', type: 'line', showDataPoints: true }],
}))

const revenueChartConfig = computed(() => ({
  title: t('analytics.revenueTrendTitle'),
  data: (revenue.data || []).map((r) => ({ ...r, revenue_major: r.revenue_minor / 100 })),
  xAxis: { key: 'date', type: 'time' },
  yAxis: {},
  series: [{ name: 'revenue_major', type: 'bar' }],
}))

const adrRevparChartConfig = computed(() => ({
  title: t('analytics.adrRevparTrendTitle'),
  data: (adrRevpar.data || []).map((r) => ({ ...r, adr_major: r.adr_minor / 100, revpar_major: r.revpar_minor / 100 })),
  xAxis: { key: 'date', type: 'time' },
  yAxis: {},
  series: [
    { name: 'adr_major', type: 'line', showDataPoints: true },
    { name: 'revpar_major', type: 'line', showDataPoints: true },
  ],
}))
</script>
