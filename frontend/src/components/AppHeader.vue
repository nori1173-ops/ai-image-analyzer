<script setup lang="ts">
defineProps<{
  user: { username?: string; signInDetails?: { loginId?: string } } | undefined
  signOut: () => void
}>()
</script>

<template>
  <v-app-bar color="surface" elevation="2">
    <v-app-bar-title>
      <v-icon icon="mdi-image-search" class="mr-2" />
      Image Analysis
    </v-app-bar-title>

    <template v-slot:append>
      <v-btn
        variant="text"
        size="small"
        href="https://openapi.example-cloud.com/image-analysis/"
        target="_blank"
        rel="noopener"
        class="mr-2"
      >
        <v-icon icon="mdi-book-open-variant" start />
        API仕様（Swagger）
      </v-btn>
      <span class="text-body-2 mr-4">
        <v-icon icon="mdi-account" size="small" class="mr-1" />
        {{ user?.signInDetails?.loginId || user?.username || 'User' }}
      </span>
      <v-btn variant="outlined" size="small" @click="signOut">
        <v-icon icon="mdi-logout" start />
        Sign Out
      </v-btn>
    </template>
  </v-app-bar>
</template>
