<script setup lang="ts">
defineProps<{
  modelValue: boolean
  src: string
  title: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="90vw"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <span class="text-truncate">{{ title }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          aria-label="閉じる"
          @click="emit('update:modelValue', false)"
        />
      </v-card-title>
      <v-card-text class="d-flex justify-center pa-2">
        <v-img :src="src" max-width="90vw" max-height="85vh" contain />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
