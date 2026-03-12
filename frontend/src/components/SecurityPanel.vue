<script setup lang="ts">
import { ref } from 'vue'

interface SecurityItem {
  title: string
  description: string
  icon: string
}

const items: SecurityItem[] = [
  {
    title: 'Encrypted Communication',
    description: 'All traffic is encrypted via HTTPS (TLS 1.2+).',
    icon: 'mdi-lock-outline',
  },
  {
    title: 'IP Restriction',
    description: 'Access is restricted to whitelisted IP addresses via CloudFront Function.',
    icon: 'mdi-shield-lock-outline',
  },
  {
    title: 'Cognito Authentication',
    description: 'User authentication powered by AWS Cognito prevents unauthorized access.',
    icon: 'mdi-account-check-outline',
  },
  {
    title: 'API Authorization',
    description: 'All API endpoints are protected by Cognito Authorizer on API Gateway.',
    icon: 'mdi-api',
  },
  {
    title: 'Zero Data Retention',
    description: 'Uploaded images are discarded immediately after analysis. No server-side storage.',
    icon: 'mdi-delete-clock-outline',
  },
  {
    title: 'Tokyo Region (ap-northeast-1)',
    description: 'All AWS resources are deployed in the Tokyo region for low latency and data residency.',
    icon: 'mdi-map-marker-check-outline',
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
  <v-card elevation="1" rounded="lg">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-shield-check-outline" class="mr-2" color="success" />
      Security Features
    </v-card-title>

    <v-card-text>
      <v-list density="compact">
        <v-list-item
          v-for="item in items"
          :key="item.title"
          @click="showDetail(item)"
          class="rounded-lg mb-1"
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
          <v-btn variant="text" color="primary" @click="showDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
