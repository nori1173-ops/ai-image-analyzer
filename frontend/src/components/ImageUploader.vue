<script setup lang="ts">
import { ref } from 'vue'
import ImageLightbox from './ImageLightbox.vue'

withDefaults(defineProps<{
  title?: string
}>(), {
  title: '画像アップロード',
})

const emit = defineEmits<{
  update: [base64: string, preview: string]
}>()

const preview = ref('')
const fileName = ref('')
const isDragging = ref(false)
const error = ref('')
const fileInput = ref<HTMLInputElement>()
const lightboxOpen = ref(false)

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

function applyDataUrl(dataUrl: string, name: string) {
  error.value = ''
  preview.value = dataUrl
  fileName.value = name
  const base64 = dataUrl.split(',')[1] ?? ''
  emit('update', base64, dataUrl)
}

defineExpose({ applyDataUrl })
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-cloud-upload" class="mr-2" />
      {{ title }}
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
          <v-icon icon="mdi-image-plus" size="64" color="primary" />
          <p class="mt-2 text-body-1">ドラッグ&ドロップ または クリックして画像を選択</p>
          <p class="text-body-2 text-medium-emphasis">JPG, PNG (最大20MB)</p>
        </div>

        <div v-else class="text-center">
          <v-img :src="preview" max-height="200" contain class="mx-auto" />
          <v-btn
            icon="mdi-magnify-plus-outline"
            size="small"
            variant="text"
            aria-label="画像を拡大表示"
            @click.stop="lightboxOpen = true"
          />
          <p class="mt-2 text-body-2">{{ fileName }}</p>
        </div>
      </div>

      <v-alert v-if="error" type="error" variant="tonal" class="mt-2" density="compact">
        {{ error }}
      </v-alert>
    </v-card-text>

    <ImageLightbox v-model="lightboxOpen" :src="preview" :title="fileName || title" />
  </v-card>
</template>

<style scoped>
.drop-zone {
  border: 2px dashed rgba(96, 165, 250, 0.4);
  border-radius: 8px;
  padding: 32px 16px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: rgb(96, 165, 250);
  background-color: rgba(96, 165, 250, 0.05);
}
</style>
