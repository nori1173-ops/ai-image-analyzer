import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PlatformInfoDialog from '../PlatformInfoDialog.vue'

const stubs = {
  VBtn: {
    emits: ['click'],
    template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
  },
  VDialog: {
    props: ['modelValue'],
    template: '<div v-if="modelValue"><slot /></div>',
  },
  VCard: { template: '<section><slot /></section>' },
  VCardTitle: { template: '<h2><slot /></h2>' },
  VCardText: { template: '<div><slot /></div>' },
  VCardActions: { template: '<div><slot /></div>' },
  VSpacer: { template: '<span />' },
}

describe('PlatformInfoDialog', () => {
  it('ヘルプボタンのクリックでプラットフォーム説明を表示する', async () => {
    const wrapper = mount(PlatformInfoDialog, { global: { stubs } })

    expect(wrapper.text()).not.toContain('AIプラットフォームについて')

    await wrapper.get('[aria-label="AIプラットフォームについて"]').trigger('click')

    expect(wrapper.text()).toContain('AIプラットフォームについて')
    expect(wrapper.text()).toContain('Amazon Bedrock（AWS内完結）')
    expect(wrapper.text()).toContain('Claude Platform on AWS（Anthropic運営）')
    expect(wrapper.text()).toContain('機密性の高い画像を扱う場合は Bedrock を推奨')
  })
})
