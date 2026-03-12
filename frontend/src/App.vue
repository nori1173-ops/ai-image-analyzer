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
import UsageGuide from './components/UsageGuide.vue'
import SecurityPanel from './components/SecurityPanel.vue'

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

const imageBase64 = ref('')
const imagePreview = ref('')
const loading = ref(false)
const chatLog = ref<ChatEntry[]>([])
const latestResult = ref<{ found: boolean; confidence: number } | null>(null)
let entryId = 0

async function handleAnalyze(params: { target: string; model: string; detail: string }) {
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
        detail: params.detail,
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

function handleImageChange(base64: string, preview: string) {
  imageBase64.value = base64
  imagePreview.value = preview
}
</script>

<template>
  <authenticator>
    <template v-slot="{ user, signOut }">
      <v-app>
        <AppHeader :user="user" :sign-out="signOut!" />

        <v-main>
          <v-container fluid class="pa-6" style="max-width: 1400px">
            <v-row>
              <v-col cols="12" md="6">
                <ImageUploader @update="handleImageChange" />
                <AnalysisForm
                  class="mt-4"
                  :loading="loading"
                  :has-image="!!imageBase64"
                  @analyze="handleAnalyze"
                />
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
