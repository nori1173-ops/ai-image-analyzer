import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ImageLightbox from '../ImageLightbox.vue'
import TemplateGallery from '../TemplateGallery.vue'

const mocks = vi.hoisted(() => ({
  remove: vi.fn(),
}))

vi.mock('../../templates', async () => {
  const { ref } = await import('vue')
  return {
    useTemplates: () => ({
      templates: ref([{
        id: 'template-1',
        name: '削除対象.png',
        dataUrl: 'data:image/png;base64,test',
      }]),
      add: vi.fn(),
      remove: mocks.remove,
    }),
  }
})

const stubs = {
  VDialog: {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<div v-if="modelValue" class="dialog-overlay" @click.self="$emit(\'update:modelValue\', false)"><slot /></div>',
  },
  VCard: { template: '<section><slot /></section>' },
  VCardTitle: { template: '<header><slot /></header>' },
  VCardText: { template: '<div><slot /></div>' },
  VCardActions: { template: '<div><slot /></div>' },
  VSpacer: { template: '<span />' },
  VRow: { template: '<div><slot /></div>' },
  VCol: { template: '<div><slot /></div>' },
  VBtn: {
    emits: ['click'],
    template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
  },
  VIcon: true,
  VImg: {
    props: ['src'],
    template: '<img :src="src">',
  },
  VAlert: { template: '<div><slot /></div>' },
  ImageLightbox: true,
}

describe('ImageLightbox', () => {
  it('shows the supplied title and image while open', () => {
    const wrapper = mount(ImageLightbox, {
      props: {
        modelValue: true,
        src: 'data:image/png;base64,test',
        title: '拡大する画像',
      },
      global: {
        stubs,
      },
    })

    expect(wrapper.text()).toContain('拡大する画像')
    expect(wrapper.get('img').attributes('src')).toBe('data:image/png;base64,test')
  })

  it('closes when the close button is clicked', async () => {
    const wrapper = mount(ImageLightbox, {
      props: {
        modelValue: true,
        src: 'data:image/png;base64,test',
        title: '拡大する画像',
      },
      global: {
        stubs,
      },
    })

    await wrapper.get('[aria-label="閉じる"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })

  it('forwards an overlay close request', async () => {
    const wrapper = mount(ImageLightbox, {
      props: {
        modelValue: true,
        src: 'data:image/png;base64,test',
        title: '拡大する画像',
      },
      global: {
        stubs,
      },
    })

    await wrapper.get('.dialog-overlay').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})

describe('TemplateGallery', () => {
  it('削除確認後にのみテンプレートを削除する', async () => {
    const wrapper = mount(TemplateGallery, {
      props: { mode: 'single' },
      global: { stubs },
    })

    await wrapper.get('button[icon="mdi-delete"]').trigger('click')

    expect(wrapper.text()).toContain('テンプレート「削除対象.png」を削除しますか？')
    expect(mocks.remove).not.toHaveBeenCalled()

    const deleteButton = wrapper.findAll('button').find((button) => button.text() === '削除')
    await deleteButton!.trigger('click')

    expect(mocks.remove).toHaveBeenCalledWith('template-1')
  })
})
