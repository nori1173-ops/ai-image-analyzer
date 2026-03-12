<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  update: [base64: string, preview: string]
}>()

const preview = ref('')
const fileName = ref('')
const isDragging = ref(false)
const error = ref('')
const fileInput = ref<HTMLInputElement>()

const MAX_SIZE = 20 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png']

function processFile(file: File) {
  error.value = ''

  if (!ACCEPTED_TYPES.includes(file.type)) {
    error.value = 'JPGまたはPNG形式の画像を選択してください'
    return
  }
  if (file.size > MAX_SIZE) {
    error.value = 'ファイルサイズは20MB以下にしてください'
    return
  }

  fileName.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    const dataUrl = e.target?.result as string
    preview.value = dataUrl
    const base64 = dataUrl.split(',')[1] ?? ''
    emit('update', base64, dataUrl)
  }
  reader.readAsDataURL(file)
}

function onFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files?.[0]) {
    processFile(target.files[0])
  }
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files?.[0]) {
    processFile(event.dataTransfer.files[0])
  }
}

function openFileDialog() {
  fileInput.value?.click()
}
</script>

<template>
  <v-card elevation="1" rounded="lg">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-tray-arrow-up" class="mr-2" color="primary" />
      画像を選択
    </v-card-title>

    <v-card-text>
      <div
        class="drop-zone"
        :class="{ 'drop-zone--active': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="onDrop"
        @click="openFileDialog"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png"
          style="display: none"
          @change="onFileSelect"
        />

        <div v-if="!preview" class="text-center">
          <v-icon icon="mdi-file-image-plus-outline" size="56" color="primary" />
          <p class="mt-3 text-body-1 font-weight-medium">ここに画像をドロップ</p>
          <p class="text-body-2 text-medium-emphasis">またはクリックして選択 (JPG / PNG, 20MB以下)</p>
        </div>

        <div v-else class="text-center">
          <v-img :src="preview" max-height="240" contain class="mx-auto rounded-lg" />
          <p class="mt-2 text-body-2 text-medium-emphasis">{{ fileName }}</p>
        </div>
      </div>

      <v-alert v-if="error" type="error" variant="tonal" class="mt-2" density="compact">
        {{ error }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.drop-zone {
  border: 2px dashed rgba(79, 70, 229, 0.3);
  border-radius: 12px;
  padding: 40px 16px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
  background-color: rgba(79, 70, 229, 0.02);
}

.drop-zone:hover,
.drop-zone--active {
  border-color: rgb(79, 70, 229);
  background-color: rgba(79, 70, 229, 0.06);
}
</style>
