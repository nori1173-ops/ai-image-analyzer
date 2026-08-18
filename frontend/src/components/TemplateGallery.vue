<script setup lang="ts">
import { ref } from 'vue'
import { useTemplates } from '../templates'
import ImageLightbox from './ImageLightbox.vue'

defineProps<{
  mode: 'single' | 'compare'
}>()

const emit = defineEmits<{
  apply: [dataUrl: string, slot: 'single' | 'before' | 'after', name: string]
}>()

const { templates, add, remove } = useTemplates()
const fileInput = ref<HTMLInputElement>()
const error = ref('')
const lightboxOpen = ref(false)
const lightboxImage = ref<{ dataUrl: string; name: string } | null>(null)
const deleteDialogOpen = ref(false)
const templateToDelete = ref<{ id: string; name: string } | null>(null)

const MAX_SIZE = 2 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png']

function openFileDialog() {
  fileInput.value?.click()
}

function openLightbox(dataUrl: string, name: string) {
  lightboxImage.value = { dataUrl, name }
  lightboxOpen.value = true
}

function requestDelete(id: string, name: string) {
  templateToDelete.value = { id, name }
  deleteDialogOpen.value = true
}

function deleteTemplate() {
  if (!templateToDelete.value) return
  remove(templateToDelete.value.id)
  deleteDialogOpen.value = false
  templateToDelete.value = null
}

function onFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return
  error.value = ''
  if (!ACCEPTED_TYPES.includes(file.type)) {
    error.value = 'JPGまたはPNG形式の画像を選択してください'
    return
  }
  if (file.size > MAX_SIZE) {
    error.value = 'テンプレートは2MB以下の画像にしてください'
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    const addError = add(file.name, e.target?.result as string)
    if (addError) error.value = addError
  }
  reader.readAsDataURL(file)
}
</script>

<template>
  <v-card>
    <v-card-title class="text-h6 d-flex align-center">
      <v-icon icon="mdi-image-multiple" class="mr-2" />
      テンプレート画像
      <v-spacer />
      <v-btn
        size="small"
        color="primary"
        variant="tonal"
        prepend-icon="mdi-plus"
        @click="openFileDialog"
      >
        追加
      </v-btn>
    </v-card-title>

    <v-card-text>
      <input
        ref="fileInput"
        type="file"
        accept="image/jpeg,image/png"
        style="display: none"
        @change="onFileSelect"
      />

      <p v-if="templates.length === 0" class="text-body-2 text-medium-emphasis">
        「追加」からよく使う画像を登録すると、ワンクリックで解析画像にセットできます（このブラウザに保存されます）
      </p>

      <v-row v-else dense>
        <v-col v-for="tpl in templates" :key="tpl.id" cols="6" sm="4">
          <v-card variant="outlined">
            <v-img
              :src="tpl.dataUrl"
              height="90"
              cover
              class="template-thumbnail"
              role="button"
              tabindex="0"
              @click="openLightbox(tpl.dataUrl, tpl.name)"
              @keydown.enter="openLightbox(tpl.dataUrl, tpl.name)"
              @keydown.space.prevent="openLightbox(tpl.dataUrl, tpl.name)"
            />
            <v-card-text class="pa-2 text-caption text-truncate">{{ tpl.name }}</v-card-text>
            <v-card-actions class="pa-1">
              <template v-if="mode === 'compare'">
                <v-btn
                  size="x-small"
                  variant="tonal"
                  color="primary"
                  @click="emit('apply', tpl.dataUrl, 'before', tpl.name)"
                >
                  前回へ
                </v-btn>
                <v-btn
                  size="x-small"
                  variant="tonal"
                  color="secondary"
                  @click="emit('apply', tpl.dataUrl, 'after', tpl.name)"
                >
                  今回へ
                </v-btn>
              </template>
              <v-btn
                v-else
                size="x-small"
                variant="tonal"
                color="primary"
                @click="emit('apply', tpl.dataUrl, 'single', tpl.name)"
              >
                セット
              </v-btn>
              <v-spacer />
              <v-btn
                size="x-small"
                icon="mdi-delete"
                variant="text"
                @click="requestDelete(tpl.id, tpl.name)"
              />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <v-alert v-if="error" type="error" variant="tonal" class="mt-2" density="compact">
        {{ error }}
      </v-alert>
    </v-card-text>

    <ImageLightbox
      v-model="lightboxOpen"
      :src="lightboxImage?.dataUrl ?? ''"
      :title="lightboxImage?.name ?? ''"
    />

    <v-dialog v-model="deleteDialogOpen" max-width="400">
      <v-card>
        <v-card-title class="text-h6">テンプレートを削除</v-card-title>
        <v-card-text>
          テンプレート「{{ templateToDelete?.name }}」を削除しますか？
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialogOpen = false">キャンセル</v-btn>
          <v-btn color="error" variant="flat" @click="deleteTemplate">削除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<style scoped>
.template-thumbnail {
  cursor: zoom-in;
}
</style>
