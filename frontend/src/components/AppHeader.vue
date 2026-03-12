<script setup lang="ts">
defineProps<{
  user: { username?: string; signInDetails?: { loginId?: string } } | undefined
  signOut: () => void
}>()
</script>

<template>
  <v-app-bar color="primary" elevation="0" density="comfortable">
    <v-app-bar-title>
      <v-icon icon="mdi-image-filter-center-focus" class="mr-2" />
      AI Image Analyzer
    </v-app-bar-title>

    <template v-slot:append>
      <v-chip variant="tonal" color="white" size="small" class="mr-3">
        <v-icon icon="mdi-account-circle" start size="small" />
        {{ user?.signInDetails?.loginId || user?.username || 'User' }}
      </v-chip>
      <v-btn variant="tonal" color="white" size="small" @click="signOut">
        <v-icon icon="mdi-logout" start />
        Logout
      </v-btn>
    </template>
  </v-app-bar>
</template>
