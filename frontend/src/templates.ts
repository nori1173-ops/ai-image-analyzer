import { ref } from 'vue'

export interface ImageTemplate {
  id: string
  name: string
  dataUrl: string
}

const STORAGE_KEY = 'image-analysis.templates'

function load(): ImageTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const templates = ref<ImageTemplate[]>(load())

function save(): string {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates.value))
    return ''
  } catch {
    return 'ブラウザの保存容量を超えました。不要なテンプレートを削除してください'
  }
}

export function useTemplates() {
  function add(name: string, dataUrl: string): string {
    const entry: ImageTemplate = {
      id: `tpl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      name,
      dataUrl,
    }
    templates.value = [...templates.value, entry]
    const error = save()
    if (error) {
      templates.value = templates.value.filter((t) => t.id !== entry.id)
    }
    return error
  }

  function remove(id: string) {
    templates.value = templates.value.filter((t) => t.id !== id)
    save()
  }

  return { templates, add, remove }
}
