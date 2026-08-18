import { describe, expect, it } from 'vitest'
import {
  DEFAULT_MODEL,
  effectivePricing,
  estimateCost,
  MODELS,
  MONITORING_COUNTS,
  TOKEN_PROFILES,
} from '../models'

describe('models', () => {
  it('Fable 5をBedrockの対応モデルに含めない', () => {
    expect(MODELS.map((model) => model.value)).not.toContain('anthropic.claude-fable-5')
    expect(MODELS.filter((model) => model.platform === 'bedrock')).toHaveLength(9)
  })

  it('全モデルに0.5刻みの賢さ目安を設定する', () => {
    expect(Object.fromEntries(MODELS.map((model) => [model.value, model.intelligence]))).toEqual({
      'anthropic.claude-sonnet-5': 8.5,
      'anthropic.claude-haiku-4-5': 6,
      'anthropic.claude-opus-4-7': 9,
      'anthropic.claude-opus-4-8': 9.5,
      'openai.gpt-5.6-terra': 8,
      'openai.gpt-5.6-luna': 6.5,
      'openai.gpt-5.6-sol': 9,
      'openai.gpt-5.5': 8.5,
      'openai.gpt-5.4': 7.5,
      'claude-sonnet-5': 8.5,
      'claude-haiku-4-5': 6,
      'claude-sonnet-4-6': 7.5,
    })
    expect(MODELS.every((model) => (
      model.intelligence >= 0
      && model.intelligence <= 10
      && Number.isInteger(model.intelligence * 2)
    ))).toBe(true)
  })

  it('Sonnet 5の導入価格を2026年8月31日まで適用する', () => {
    const model = MODELS.find((item) => item.value === DEFAULT_MODEL)!

    expect(model.pricingNote).toBe('2026-09-01以降 $3/$15')
    expect(effectivePricing(model, new Date('2026-08-31T14:59:59.999Z'))).toEqual({
      input: 2,
      output: 10,
      pricingNote: '2026-09-01以降 $3/$15',
    })
  })

  it('Sonnet 5の価格を2026年9月1日から通常価格へ切り替える', () => {
    const model = MODELS.find((item) => item.value === DEFAULT_MODEL)!

    expect(effectivePricing(model, new Date('2026-08-31T15:00:00.000Z'))).toEqual({
      input: 3,
      output: 15,
    })
  })

  it('プロバイダーと操作に応じたトークンプロファイルでコストを算出する', () => {
    expect(TOKEN_PROFILES.anthropic.compare).toEqual({ input: 3650, output: 250 })
    expect(MONITORING_COUNTS).toEqual({ tenMin: 4320, oneHour: 720 })

    const cost = estimateCost('anthropic.claude-haiku-4-5', 'analyze')

    expect(cost.perRequestUsd).toBeCloseTo(0.00255)
    expect(cost.perRequestJpy).toBeCloseTo(0.39525)
    expect(cost.monthly10MinUsd).toBeCloseTo(11.016)
    expect(cost.monthlyHourlyUsd).toBeCloseTo(1.836)
  })

  it('Sonnet 5の切替後価格をコスト計算へ反映する', () => {
    const introductionPrice = estimateCost(
      DEFAULT_MODEL,
      'compare',
      new Date('2026-08-31T14:59:59.999Z'),
    )
    const regularPrice = estimateCost(
      DEFAULT_MODEL,
      'compare',
      new Date('2026-08-31T15:00:00.000Z'),
    )

    expect(introductionPrice.perRequestUsd).toBeCloseTo(0.0098, 7)
    expect(regularPrice.perRequestUsd).toBeCloseTo(0.0147, 7)
  })

  it('存在しないモデルのコスト計算を拒否する', () => {
    expect(() => estimateCost('unknown-model', 'compare')).toThrow('Unknown model: unknown-model')
  })
})
