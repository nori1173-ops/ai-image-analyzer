<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  loading: boolean
  hasImage: boolean
}>()

const emit = defineEmits<{
  analyze: [params: { target: string; model: string; detail: string }]
}>()

const target = ref('')
const model = ref('gpt-4.1-mini')
const detail = ref('auto')

const models = [
  { title: 'GPT-4.1 Mini（推奨・低コスト）', value: 'gpt-4.1-mini' },
  { title: 'GPT-4.1', value: 'gpt-4.1' },
  { title: 'GPT-4.1 Nano', value: 'gpt-4.1-nano' },
  { title: 'GPT-4o', value: 'gpt-4o' },
  { title: 'GPT-4o Mini', value: 'gpt-4o-mini' },
]

const resolutions = [
  { title: 'Low', value: 'low' },
  { title: 'High', value: 'high' },
  { title: 'Auto', value: 'auto' },
]

function submit() {
  if (!target.value.trim()) return
  emit('analyze', {
    target: target.value.trim(),
    model: model.value,
    detail: detail.value,
  })
}
</script>

<template>
  <v-card elevation="1" rounded="lg">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-tune-variant" class="mr-2" color="primary" />
      解析パラメータ
    </v-card-title>

    <v-card-text>
      <v-text-field
        v-model="target"
        label="検出ターゲット"
        placeholder="例: cracks, vehicles, people..."
        variant="outlined"
        density="comfortable"
        color="primary"
        :rules="[v => !!v.trim() || '必須項目です']"
        prepend-inner-icon="mdi-crosshairs-gps"
      />

      <v-row>
        <v-col cols="6">
          <v-select
            v-model="model"
            :items="models"
            label="AIモデル"
            variant="outlined"
            density="comfortable"
            color="primary"
          />
        </v-col>
        <v-col cols="6">
          <v-select
            v-model="detail"
            :items="resolutions"
            label="画像解像度"
            variant="outlined"
            density="comfortable"
            color="primary"
          />
        </v-col>
      </v-row>

      <v-btn
        color="primary"
        size="large"
        block
        rounded="lg"
        :loading="loading"
        :disabled="!hasImage || !target.trim() || loading"
        @click="submit"
      >
        <v-icon icon="mdi-play-circle-outline" start />
        解析を実行
      </v-btn>
    </v-card-text>
  </v-card>
</template>
