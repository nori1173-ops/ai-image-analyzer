<script setup lang="ts">
import { ref } from 'vue'
import { Authenticator } from '@aws-amplify/ui-vue'
import '@aws-amplify/ui-vue/styles.css'
import { fetchAuthSession } from 'aws-amplify/auth'
import AppHeader from './components/AppHeader.vue'
import ImageUploader from './components/ImageUploader.vue'
import AnalysisForm from './components/AnalysisForm.vue'
import AnalysisResult from './components/AnalysisResult.vue'
import ChatLog from './components/ChatLog.vue'
import CompareForm from './components/CompareForm.vue'
import CompareResult, { type CompareResultData } from './components/CompareResult.vue'
import TemplateGallery from './components/TemplateGallery.vue'
import UsageGuide from './components/UsageGuide.vue'
import SecurityPanel from './components/SecurityPanel.vue'
import { parseRecipientList } from './notifications'

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

interface CompareHistoryEntry {
  id: number
  perspective: string
  danger: boolean
  riskLevel: string
  timestamp: Date
}

const mode = ref<'single' | 'compare'>('single')

const imageBase64 = ref('')
const imagePreview = ref('')
const loading = ref(false)
const chatLog = ref<ChatEntry[]>([])
const latestResult = ref<{ found: boolean; confidence: number } | null>(null)
let entryId = 0

const beforeBase64 = ref('')
const afterBase64 = ref('')
const compareLoading = ref(false)
const compareResult = ref<CompareResultData | null>(null)
const compareError = ref('')
const compareHistory = ref<CompareHistoryEntry[]>([])
let compareId = 0

async function handleAnalyze(params: { target: string; model: string }) {
  if (!imageBase64.value) return
  loading.value = true
  latestResult.value = null

  const startTime = Date.now()
  try {
    const session = await fetchAuthSession()
    const token = session.tokens?.idToken?.toString()

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        image: imageBase64.value,
        target: params.target,
        model: params.model,
      }),
    })

    const data = await response.json()
    const responseTime = Date.now() - startTime

    if (!response.ok || data.error) {
      const errMsg = data.error || `HTTP ${response.status}`
      latestResult.value = { found: false, confidence: 0 }
      chatLog.value.push({
        id: ++entryId,
        target: params.target,
        imagePreview: imagePreview.value,
        found: false,
        confidence: 0,
        description: `エラー: ${errMsg}`,
        tokens: 0,
        responseTime,
        timestamp: new Date(),
      })
      return
    }

    latestResult.value = {
      found: !!data.found,
      confidence: Number(data.confidence) || 0,
    }

    chatLog.value.push({
      id: ++entryId,
      target: params.target,
      imagePreview: imagePreview.value,
      found: !!data.found,
      confidence: Number(data.confidence) || 0,
      description: data.answer || data.description || '',
      tokens: data.usage?.total_tokens || 0,
      responseTime,
      timestamp: new Date(),
    })
  } catch (error) {
    console.error('Analysis failed:', error)
    latestResult.value = { found: false, confidence: 0 }
    chatLog.value.push({
      id: ++entryId,
      target: '(不明)',
      imagePreview: imagePreview.value,
      found: false,
      confidence: 0,
      description: `通信エラー: ${error instanceof Error ? error.message : String(error)}`,
      tokens: 0,
      responseTime: Date.now() - startTime,
      timestamp: new Date(),
    })
  } finally {
    loading.value = false
  }
}

async function handleCompare(params: {
  perspective: string
  model: string
  notify: boolean
  notifyTo: string
  notifyCc: string
  notifyBcc: string
  notifyLine: boolean
}) {
  if (!beforeBase64.value || !afterBase64.value) return
  compareLoading.value = true
  compareResult.value = null
  compareError.value = ''

  try {
    const session = await fetchAuthSession()
    const token = session.tokens?.idToken?.toString()

    const requestBody: {
      before_image: string
      after_image: string
      perspective: string
      model: string
      notify: boolean
      notify_to?: string[]
      notify_cc?: string[]
      notify_bcc?: string[]
      notify_line?: true
    } = {
      before_image: beforeBase64.value,
      after_image: afterBase64.value,
      perspective: params.perspective,
      model: params.model,
      notify: params.notify,
    }

    if (params.notify) {
      const notifyTo = parseRecipientList(params.notifyTo)
      const notifyCc = parseRecipientList(params.notifyCc)
      const notifyBcc = parseRecipientList(params.notifyBcc)

      if (notifyTo.length > 0) requestBody.notify_to = notifyTo
      if (notifyCc.length > 0) requestBody.notify_cc = notifyCc
      if (notifyBcc.length > 0) requestBody.notify_bcc = notifyBcc
    }
    if (params.notifyLine) requestBody.notify_line = true

    const response = await fetch('/api/compare', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(requestBody),
    })

    const data = await response.json()

    if (!response.ok || data.error) {
      compareError.value = data.error || `HTTP ${response.status}`
      return
    }

    compareResult.value = data
    compareHistory.value.unshift({
      id: ++compareId,
      perspective: params.perspective,
      danger: !!data.danger,
      riskLevel: data.risk_level,
      timestamp: new Date(),
    })
  } catch (error) {
    console.error('Compare failed:', error)
    compareError.value = `通信エラー: ${error instanceof Error ? error.message : String(error)}`
  } finally {
    compareLoading.value = false
  }
}

function handleImageChange(base64: string, preview: string) {
  imageBase64.value = base64
  imagePreview.value = preview
}

interface UploaderExposed {
  applyDataUrl: (dataUrl: string, name: string) => void
}

const singleUploader = ref<UploaderExposed | null>(null)
const beforeUploader = ref<UploaderExposed | null>(null)
const afterUploader = ref<UploaderExposed | null>(null)

function handleTemplateApply(dataUrl: string, slot: 'single' | 'before' | 'after', name: string) {
  const uploader =
    slot === 'single' ? singleUploader.value :
    slot === 'before' ? beforeUploader.value :
    afterUploader.value
  uploader?.applyDataUrl(dataUrl, name)
}

function handleBeforeChange(base64: string) {
  beforeBase64.value = base64
}

function handleAfterChange(base64: string) {
  afterBase64.value = base64
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
}

const RISK_LABEL: Record<string, string> = {
  none: 'なし',
  low: '低',
  medium: '中',
  high: '高',
}
</script>

<template>
  <authenticator>
    <template v-slot="{ user, signOut }">
      <v-app>
        <AppHeader :user="user" :sign-out="signOut!" />

        <v-main>
          <v-container fluid class="pa-4">
            <v-tabs v-model="mode" color="primary" bg-color="surface" class="mb-4">
              <v-tab value="single" color="primary" base-color="primary">
                <v-icon icon="mdi-image-search" start />
                単一画像解析
              </v-tab>
              <v-tab value="compare" color="primary" base-color="primary">
                <v-icon icon="mdi-compare" start />
                画像比較（災害差分監視）
              </v-tab>
            </v-tabs>

            <v-window v-model="mode">
              <v-window-item value="single">
                <v-row>
                  <v-col cols="12" md="6">
                    <ImageUploader ref="singleUploader" @update="handleImageChange" />
                    <AnalysisForm
                      class="mt-4"
                      :loading="loading"
                      :has-image="!!imageBase64"
                      @analyze="handleAnalyze"
                    />
                    <TemplateGallery mode="single" class="mt-4" @apply="handleTemplateApply" />
                  </v-col>

                  <v-col cols="12" md="6">
                    <AnalysisResult
                      v-if="latestResult"
                      :found="latestResult.found"
                      :confidence="latestResult.confidence"
                    />
                    <ChatLog :entries="chatLog" class="mt-4" />
                  </v-col>
                </v-row>
              </v-window-item>

              <v-window-item value="compare">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-row>
                      <v-col cols="12" sm="6">
                        <ImageUploader ref="beforeUploader" title="前回の画像" @update="handleBeforeChange" />
                      </v-col>
                      <v-col cols="12" sm="6">
                        <ImageUploader ref="afterUploader" title="今回の画像" @update="handleAfterChange" />
                      </v-col>
                    </v-row>
                    <CompareForm
                      class="mt-4"
                      :loading="compareLoading"
                      :has-before="!!beforeBase64"
                      :has-after="!!afterBase64"
                      @compare="handleCompare"
                    />
                    <TemplateGallery mode="compare" class="mt-4" @apply="handleTemplateApply" />
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-alert
                      v-if="compareError"
                      type="error"
                      variant="tonal"
                      class="mb-4"
                    >
                      {{ compareError }}
                    </v-alert>

                    <CompareResult v-if="compareResult" :result="compareResult" />

                    <v-card v-if="compareHistory.length > 0" class="mt-4">
                      <v-card-title class="text-h6">
                        <v-icon icon="mdi-history" class="mr-2" />
                        比較履歴
                      </v-card-title>
                      <v-card-text>
                        <v-list density="compact">
                          <v-list-item
                            v-for="entry in compareHistory"
                            :key="entry.id"
                            class="rounded mb-1"
                          >
                            <template v-slot:prepend>
                              <v-icon
                                :icon="entry.danger ? 'mdi-alert' : 'mdi-shield-check'"
                                :color="entry.danger ? 'error' : 'success'"
                                size="small"
                              />
                            </template>
                            <v-list-item-title class="text-body-2">
                              {{ entry.perspective }}
                            </v-list-item-title>
                            <template v-slot:append>
                              <span class="text-caption text-medium-emphasis mr-2">
                                {{ RISK_LABEL[entry.riskLevel] ?? entry.riskLevel }}
                              </span>
                              <span class="text-caption text-medium-emphasis">
                                {{ formatTime(entry.timestamp) }}
                              </span>
                            </template>
                          </v-list-item>
                        </v-list>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-window-item>
            </v-window>

            <v-row class="mt-4">
              <v-col cols="12" md="6">
                <UsageGuide />
              </v-col>
              <v-col cols="12" md="6">
                <SecurityPanel />
              </v-col>
            </v-row>
          </v-container>
        </v-main>
      </v-app>
    </template>
  </authenticator>
</template>
