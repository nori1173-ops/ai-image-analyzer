<script setup lang="ts">
import { ref } from 'vue'

interface SecurityItem {
  title: string
  description: string
  icon: string
}

const items: SecurityItem[] = [
  {
    title: 'SSL/TLS暗号化',
    description: 'すべての通信はHTTPS (TLS 1.2+) で暗号化されています。',
    icon: 'mdi-lock',
  },
  {
    title: 'IP制限',
    description: '許可されたIPアドレスからのみアクセス可能です。',
    icon: 'mdi-shield-lock',
  },
  {
    title: 'Cognito認証',
    description: 'AWS Cognitoによるユーザー認証で不正アクセスを防止します。',
    icon: 'mdi-account-check',
  },
  {
    title: 'API保護',
    description: 'エンドポイントごとに保護しています。/analyze・/compare はCognito JWT認証＋オリジン検証、/workflow/analyze・/workflow/compare はAPIキー認証（90日自動ローテーション）、/health はオリジン検証で保護します。',
    icon: 'mdi-api',
  },
  {
    title: '画像データ即破棄',
    description: 'アップロードされた画像データは解析後すぐに破棄され、サーバーに保存されません。',
    icon: 'mdi-delete-clock',
  },
  {
    title: 'AWS東京リージョン',
    description: 'すべてのリソースはap-northeast-1 (東京) リージョンで運用されています。',
    icon: 'mdi-map-marker-check',
  },
]

const selectedItem = ref<SecurityItem | null>(null)
const showDialog = ref(false)

function showDetail(item: SecurityItem) {
  selectedItem.value = item
  showDialog.value = true
}
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-shield-check" class="mr-2" />
      セキュリティ
    </v-card-title>

    <v-card-text>
      <v-list density="compact">
        <v-list-item
          v-for="item in items"
          :key="item.title"
          @click="showDetail(item)"
          class="rounded mb-1"
        >
          <template v-slot:prepend>
            <v-icon :icon="item.icon" color="success" size="small" />
          </template>
          <v-list-item-title class="text-body-2">{{ item.title }}</v-list-item-title>
          <template v-slot:append>
            <v-icon icon="mdi-chevron-right" size="small" />
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>

    <v-dialog v-model="showDialog" max-width="400">
      <v-card v-if="selectedItem">
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-check-circle" color="success" class="mr-2" />
          {{ selectedItem.title }}
        </v-card-title>
        <v-card-text>{{ selectedItem.description }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDialog = false">閉じる</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
