<script setup lang="ts">
interface ChatEntry {
  id: number
  target: string
  imagePreview: string
  found: boolean
  confidence: number
  description: string
  tokens: number
  responseTime: number
  timestamp: Date
}

defineProps<{
  entries: ChatEntry[]
}>()

function formatTime(date: Date): string {
  return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <v-card v-if="entries.length > 0">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-chat" class="mr-2" />
      解析ログ
    </v-card-title>

    <v-card-text class="chat-log">
      <div v-for="entry in entries" :key="entry.id" class="mb-4">
        <div class="d-flex align-start mb-2">
          <v-avatar color="primary" size="32" class="mr-2">
            <v-icon icon="mdi-account" size="small" />
          </v-avatar>
          <v-card variant="tonal" class="flex-grow-1">
            <v-card-text class="pa-3">
              <p class="text-body-2">「{{ entry.target }}」を探して</p>
              <v-img
                v-if="entry.imagePreview"
                :src="entry.imagePreview"
                max-height="80"
                max-width="80"
                class="mt-1 rounded"
              />
            </v-card-text>
          </v-card>
        </div>

        <div class="d-flex align-start">
          <v-avatar color="secondary" size="32" class="mr-2">
            <v-icon icon="mdi-robot" size="small" />
          </v-avatar>
          <v-card variant="tonal" class="flex-grow-1">
            <v-card-text class="pa-3">
              <div class="d-flex align-center mb-1">
                <v-icon
                  :icon="entry.found ? 'mdi-check-circle' : 'mdi-close-circle'"
                  :color="entry.found ? 'success' : 'error'"
                  size="small"
                  class="mr-1"
                />
                <span class="text-body-2 font-weight-bold">
                  {{ entry.found ? '発見' : '未検出' }} ({{ entry.confidence }}%)
                </span>
              </div>
              <p v-if="entry.description" class="text-body-2">{{ entry.description }}</p>
              <div class="d-flex text-caption text-medium-emphasis mt-2" style="gap: 12px">
                <span>
                  <v-icon icon="mdi-clock-outline" size="x-small" />
                  {{ formatTime(entry.timestamp) }}
                </span>
                <span v-if="entry.tokens">
                  <v-icon icon="mdi-numeric" size="x-small" />
                  {{ entry.tokens }} tokens
                </span>
                <span>
                  <v-icon icon="mdi-timer-outline" size="x-small" />
                  {{ (entry.responseTime / 1000).toFixed(1) }}s
                </span>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.chat-log {
  max-height: 500px;
  overflow-y: auto;
}
</style>
