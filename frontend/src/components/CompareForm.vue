<script setup lang="ts">
import { ref } from 'vue'
import { DEFAULT_MODEL, effectivePricing, MODELS } from '../models'
import CostPanel from './CostPanel.vue'
import PlatformInfoDialog from './PlatformInfoDialog.vue'

defineProps<{
  loading: boolean
  hasBefore: boolean
  hasAfter: boolean
}>()

const emit = defineEmits<{
  compare: [params: {
    perspective: string
    model: string
    notify: boolean
    notifyTo: string
    notifyCc: string
    notifyBcc: string
    notifyLine: boolean
  }]
}>()

const perspective = ref('')
const model = ref(DEFAULT_MODEL)
const notify = ref(false)
const notifyTo = ref('')
const notifyCc = ref('')
const notifyBcc = ref('')
const notifyLine = ref(false)

const modelItems = [
  { type: 'subheader', title: 'Amazon Bedrock（AWS内完結）' },
  ...MODELS
    .filter((item) => item.platform === 'bedrock')
    .map((item) => {
      const pricing = effectivePricing(item)
      return {
        ...item,
        props: {
          subtitle: `処理: ${item.region} ・ $${pricing.input}/$${pricing.output} /1Mトークン`,
        },
      }
    }),
  { type: 'divider' },
  { type: 'subheader', title: 'Claude Platform on AWS（Anthropic運営）' },
  ...MODELS
    .filter((item) => item.platform === 'cpoa')
    .map((item) => {
      const pricing = effectivePricing(item)
      return {
        ...item,
        props: {
          subtitle: `処理: ${item.region} ・ $${pricing.input}/$${pricing.output} /1Mトークン`,
        },
      }
    }),
]

function submit() {
  if (!perspective.value.trim()) return
  emit('compare', {
    perspective: perspective.value.trim(),
    model: model.value,
    notify: notify.value,
    notifyTo: notifyTo.value,
    notifyCc: notifyCc.value,
    notifyBcc: notifyBcc.value,
    notifyLine: notifyLine.value,
  })
}
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-compare" class="mr-2" />
      比較設定
    </v-card-title>

    <v-card-text>
      <v-text-field
        v-model="perspective"
        label="監視観点"
        placeholder="例: 土砂崩れ、河川水位の上昇..."
        variant="outlined"
        density="comfortable"
        :rules="[v => !!v.trim() || '必須項目です']"
        prepend-inner-icon="mdi-eye-check"
      />

      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center">
            <v-select
              v-model="model"
              :items="modelItems"
              label="モデル"
              variant="outlined"
              density="comfortable"
              class="flex-grow-1"
            />
            <div class="mb-5 ml-1">
              <PlatformInfoDialog />
            </div>
          </div>
          <CostPanel :model="model" operation="compare" />
        </v-col>
      </v-row>

      <v-checkbox
        v-model="notify"
        label="危険検知時にメール通知する"
        density="comfortable"
        hide-details
        class="mb-2"
      />

      <v-expand-transition>
        <div v-if="notify">
          <v-text-field
            v-model="notifyTo"
            label="To"
            hint="未入力時はサーバー既定の宛先に送信"
            persistent-hint
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-model="notifyCc"
            label="CC"
            hint="任意、カンマ区切り"
            persistent-hint
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-model="notifyBcc"
            label="BCC"
            hint="任意、カンマ区切り"
            persistent-hint
            variant="outlined"
            density="comfortable"
          />
        </div>
      </v-expand-transition>

      <v-checkbox
        v-model="notifyLine"
        label="LINE通知（画像付き）"
        density="comfortable"
        hide-details
        class="mb-2"
      />
      <p class="text-caption text-medium-emphasis mb-2">
        サーバー側でLINE設定が未構成の場合はスキップされます。
      </p>

      <v-btn
        color="primary"
        size="large"
        block
        :loading="loading"
        :disabled="!hasBefore || !hasAfter || !perspective.trim() || loading"
        @click="submit"
      >
        <v-icon icon="mdi-compare-horizontal" start />
        比較実行
      </v-btn>
    </v-card-text>
  </v-card>
</template>
