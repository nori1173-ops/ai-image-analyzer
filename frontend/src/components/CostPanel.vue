<script setup lang="ts">
import { computed } from 'vue'
import {
  effectivePricing,
  estimateCost,
  MODELS,
} from '../models'

const props = defineProps<{
  model: string
  operation: 'analyze' | 'compare'
}>()

const selectedModel = computed(() => MODELS.find((item) => item.value === props.model))
const pricing = computed(() => selectedModel.value && effectivePricing(selectedModel.value))
const cost = computed(() => estimateCost(props.model, props.operation))

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumSignificantDigits: 3 }).format(value)
}

function formatYen(value: number): string {
  return Math.round(value).toLocaleString('ja-JP')
}
</script>

<template>
  <v-card v-if="selectedModel && pricing" variant="tonal" density="compact" class="mt-2">
    <v-card-text class="py-3">
      <div class="d-flex align-center text-body-2 mb-1">
        <span class="mr-2">賢さ（目安）:</span>
        <v-rating
          :model-value="selectedModel.intelligence / 2"
          readonly
          half-increments
          :length="5"
          density="compact"
          size="small"
          class="mr-2"
        />
        <span>{{ selectedModel.intelligence }}/10</span>
      </div>
      <div class="text-body-2 mb-1">
        単価: 入力 ${{ pricing.input }} / 出力 ${{ pricing.output }}（100万トークンあたり）
      </div>
      <div class="text-body-2 mb-1">
        1リクエストあたり: ${{ formatUsd(cost.perRequestUsd) }}（約{{ formatYen(cost.perRequestJpy) }}円）
      </div>
      <div class="text-body-2 mb-1">
        10分間隔監視（月4,320回）: ${{ formatUsd(cost.monthly10MinUsd) }}（約{{ formatYen(cost.monthly10MinJpy) }}円/月）
      </div>
      <div class="text-body-2">
        1時間間隔監視（月720回）: ${{ formatUsd(cost.monthlyHourlyUsd) }}（約{{ formatYen(cost.monthlyHourlyJpy) }}円/月）
      </div>
      <p class="text-caption text-medium-emphasis mt-2 mb-0">
        実測トークン数に基づく概算（1280×720画像）。GPTはreasoningトークンを含む概算。為替 155円/USD。賢さは社内目安（公開ベンチマークと本用途での実測の総合印象）
      </p>
      <p v-if="pricing.pricingNote" class="text-caption text-medium-emphasis mb-0">
        {{ pricing.pricingNote }}
      </p>
    </v-card-text>
  </v-card>
</template>
