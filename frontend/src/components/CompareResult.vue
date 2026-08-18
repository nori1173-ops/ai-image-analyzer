<script lang="ts">
export interface CompareResultData {
  danger: boolean
  risk_level: string
  reason?: string
  changes?: string
  model?: string
  usage?: Record<string, number>
  elapsed_seconds?: number
  notified?: boolean
  message_id?: string
  notify_error?: string
  line_notified?: boolean
  line_skip_reason?: string
  line_error?: string
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  result: CompareResultData
}>()

const RISK_META: Record<string, { color: string; label: string }> = {
  none: { color: 'success', label: 'なし' },
  low: { color: 'warning', label: '低' },
  medium: { color: 'orange', label: '中' },
  high: { color: 'error', label: '高' },
}

const risk = computed(() => RISK_META[props.result.risk_level] ?? { color: 'grey', label: props.result.risk_level })

const totalTokens = computed(() => {
  const u = props.result.usage
  if (!u) return 0
  return u.total_tokens ?? (u.input_tokens ?? 0) + (u.output_tokens ?? 0)
})
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-alert-decagram" class="mr-2" />
      比較結果
    </v-card-title>

    <v-card-text>
      <v-alert
        :type="result.danger ? 'error' : 'success'"
        variant="tonal"
        :icon="result.danger ? 'mdi-alert' : 'mdi-shield-check'"
        class="mb-4"
      >
        <span class="text-body-1 font-weight-bold">
          {{ result.danger ? '危険を検知しました' : '危険は検知されませんでした' }}
        </span>
      </v-alert>

      <div class="d-flex align-center mb-4">
        <span class="text-body-2 mr-2">危険度</span>
        <v-chip :color="risk.color" variant="flat" size="small" label>
          {{ risk.label }}
        </v-chip>
      </div>

      <div v-if="result.reason" class="mb-3">
        <p class="text-body-2 font-weight-bold mb-1">判定理由</p>
        <p class="text-body-2">{{ result.reason }}</p>
      </div>

      <div v-if="result.changes" class="mb-3">
        <p class="text-body-2 font-weight-bold mb-1">検出された変化</p>
        <p class="text-body-2">{{ result.changes }}</p>
      </div>

      <v-alert
        v-if="result.notified"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <v-icon icon="mdi-email-check" start />
        通知メールを送信しました
        <span v-if="result.message_id" class="text-caption d-block">
          Message ID: {{ result.message_id }}
        </span>
      </v-alert>

      <v-alert
        v-if="result.notify_error"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        通知の送信に失敗しました: {{ result.notify_error }}
      </v-alert>

      <v-alert
        v-if="result.line_notified"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <v-icon icon="mdi-message-image" start />
        LINE通知を送信しました
      </v-alert>

      <v-alert
        v-else-if="result.line_skip_reason"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        LINE通知をスキップしました: {{ result.line_skip_reason }}
      </v-alert>

      <v-alert
        v-else-if="result.line_error"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        LINE通知の送信に失敗しました: {{ result.line_error }}
      </v-alert>

      <div class="d-flex flex-wrap text-caption text-medium-emphasis" style="gap: 12px">
        <span v-if="result.model">
          <v-icon icon="mdi-brain" size="x-small" />
          {{ result.model }}
        </span>
        <span v-if="totalTokens">
          <v-icon icon="mdi-numeric" size="x-small" />
          {{ totalTokens }} tokens
        </span>
        <span v-if="result.elapsed_seconds != null">
          <v-icon icon="mdi-timer-outline" size="x-small" />
          {{ result.elapsed_seconds }}s
        </span>
      </div>
    </v-card-text>
  </v-card>
</template>
