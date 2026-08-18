<script setup lang="ts">
import { ref } from 'vue'
import { DEFAULT_MODEL, effectivePricing, MODELS } from '../models'
import CostPanel from './CostPanel.vue'
import PlatformInfoDialog from './PlatformInfoDialog.vue'

defineProps<{
  loading: boolean
  hasImage: boolean
}>()

const emit = defineEmits<{
  analyze: [params: { target: string; model: string }]
}>()

const target = ref('')
const model = ref(DEFAULT_MODEL)

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
  if (!target.value.trim()) return
  emit('analyze', {
    target: target.value.trim(),
    model: model.value,
  })
}
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-magnify" class="mr-2" />
      解析設定
    </v-card-title>

    <v-card-text>
      <v-text-field
        v-model="target"
        label="見つけたいもの"
        placeholder="例: ひび割れ、人物、テキスト..."
        variant="outlined"
        density="comfortable"
        :rules="[v => !!v.trim() || '必須項目です']"
        prepend-inner-icon="mdi-target"
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
          <CostPanel :model="model" operation="analyze" />
        </v-col>
      </v-row>

      <v-btn
        color="primary"
        size="large"
        block
        :loading="loading"
        :disabled="!hasImage || !target.trim() || loading"
        @click="submit"
      >
        <v-icon icon="mdi-magnify-scan" start />
        解析開始
      </v-btn>
    </v-card-text>
  </v-card>
</template>
