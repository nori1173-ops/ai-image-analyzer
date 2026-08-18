<script setup lang="ts">
import { ref } from 'vue'

const showDialog = ref(false)
</script>

<template>
  <v-btn
    icon="mdi-help-circle-outline"
    variant="text"
    size="small"
    aria-label="AIプラットフォームについて"
    @click="showDialog = true"
  />

  <v-dialog v-model="showDialog" max-width="640">
    <v-card>
      <v-card-title>AIプラットフォームについて</v-card-title>
      <v-card-text>
        <p class="text-subtitle-1 font-weight-medium mb-2">Amazon Bedrock（AWS内完結）</p>
        <ul class="pl-5 mb-4">
          <li>AI推論がAWSのインフラ内で完結し、画像・プロンプトがAWSのセキュリティ境界の外に出ません</li>
          <li>モデル提供元（Anthropic / OpenAI）の社員も推論基盤にアクセスできません</li>
          <li>入力データがAIの学習に使われることはありません</li>
          <li>Haiku 4.5 / Opus 4.7 / Opus 4.8 は東京リージョン処理。Sonnet 5 / GPT系は米国リージョン処理（AWS境界内）</li>
          <li>請求はAWS利用料に一本化（モデル提供元との契約不要）</li>
        </ul>

        <p class="text-subtitle-1 font-weight-medium mb-2">Claude Platform on AWS（Anthropic運営）</p>
        <ul class="pl-5 mb-4">
          <li>Anthropicが運営するClaude基盤をAWSアカウント経由で利用します</li>
          <li>推論はAnthropicのインフラで実行されます（AWSのセキュリティ境界の外）</li>
          <li>新機能・新モデルが提供当日から利用できます</li>
          <li>入力データがAIの学習に使われることはありません</li>
          <li>請求はAWS請求書（AWS Marketplace経由）に含まれます</li>
        </ul>

        <p class="mb-0">
          <span class="font-weight-medium">使い分けの目安:</span>
          機密性の高い画像を扱う場合は Bedrock を推奨。最新機能をいち早く試す場合は Claude Platform on AWS。
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showDialog = false">閉じる</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
