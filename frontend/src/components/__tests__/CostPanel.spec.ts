import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CostPanel from '../CostPanel.vue'

const stubs = {
  VCard: { template: '<section><slot /></section>' },
  VCardText: { template: '<div><slot /></div>' },
  VRating: {
    props: ['modelValue', 'readonly', 'halfIncrements', 'length', 'density', 'size'],
    template: '<div data-testid="intelligence-rating" :data-model-value="modelValue" />',
  },
}

describe('CostPanel', () => {
  it('選択モデルと操作に対応する単価と監視コストを表示する', () => {
    const wrapper = mount(CostPanel, {
      props: {
        model: 'anthropic.claude-opus-4-7',
        operation: 'analyze',
      },
      global: { stubs },
    })

    expect(wrapper.text()).toContain('賢さ（目安）:')
    expect(wrapper.get('[data-testid="intelligence-rating"]').attributes('data-model-value')).toBe('4.5')
    expect(wrapper.text()).toContain('9/10')
    expect(wrapper.text()).toContain('単価: 入力 $5 / 出力 $25（100万トークンあたり）')
    expect(wrapper.text()).toContain('1リクエストあたり: $0.0128（約2円）')
    expect(wrapper.text()).toContain('10分間隔監視（月4,320回）: $55.1（約8,537円/月）')
    expect(wrapper.text()).toContain('1時間間隔監視（月720回）: $9.18（約1,423円/月）')
    expect(wrapper.text()).toContain('実測トークン数に基づく概算（1280×720画像）。GPTはreasoningトークンを含む概算。為替 155円/USD')
    expect(wrapper.text()).toContain('賢さは社内目安（公開ベンチマークと本用途での実測の総合印象）')
  })
})
