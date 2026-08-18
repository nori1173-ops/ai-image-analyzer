export type ModelPlatform = 'bedrock' | 'cpoa'
export type ModelProvider = 'anthropic' | 'openai'
export type Operation = 'analyze' | 'compare'

export interface ModelPricing {
  input: number
  output: number
}

export interface ModelOption {
  value: string
  title: string
  platform: ModelPlatform
  provider: ModelProvider
  pricing: ModelPricing
  pricingNote?: string
  intelligence: number
  region: '東京' | '米国'
}

export interface CostEstimate {
  perRequestUsd: number
  perRequestJpy: number
  monthly10MinUsd: number
  monthly10MinJpy: number
  monthlyHourlyUsd: number
  monthlyHourlyJpy: number
}

export const EXCHANGE_RATE_JPY = 155

export const MODELS: ModelOption[] = [
  {
    value: 'anthropic.claude-sonnet-5',
    title: 'Claude Sonnet 5（推奨）',
    platform: 'bedrock',
    provider: 'anthropic',
    pricing: { input: 2, output: 10 },
    pricingNote: '2026-09-01以降 $3/$15',
    intelligence: 8.5,
    region: '米国',
  },
  {
    value: 'anthropic.claude-haiku-4-5',
    title: 'Claude Haiku 4.5（低コスト）',
    platform: 'bedrock',
    provider: 'anthropic',
    pricing: { input: 1, output: 5 },
    intelligence: 6,
    region: '東京',
  },
  {
    value: 'anthropic.claude-opus-4-7',
    title: 'Claude Opus 4.7',
    platform: 'bedrock',
    provider: 'anthropic',
    pricing: { input: 5, output: 25 },
    intelligence: 9,
    region: '東京',
  },
  {
    value: 'anthropic.claude-opus-4-8',
    title: 'Claude Opus 4.8',
    platform: 'bedrock',
    provider: 'anthropic',
    pricing: { input: 5, output: 25 },
    intelligence: 9.5,
    region: '東京',
  },
  {
    value: 'openai.gpt-5.6-terra',
    title: 'GPT-5.6 Terra',
    platform: 'bedrock',
    provider: 'openai',
    pricing: { input: 2.5, output: 15 },
    intelligence: 8,
    region: '米国',
  },
  {
    value: 'openai.gpt-5.6-luna',
    title: 'GPT-5.6 Luna（低コスト）',
    platform: 'bedrock',
    provider: 'openai',
    pricing: { input: 1, output: 6 },
    intelligence: 6.5,
    region: '米国',
  },
  {
    value: 'openai.gpt-5.6-sol',
    title: 'GPT-5.6 Sol',
    platform: 'bedrock',
    provider: 'openai',
    pricing: { input: 5, output: 30 },
    intelligence: 9,
    region: '米国',
  },
  {
    value: 'openai.gpt-5.5',
    title: 'GPT-5.5',
    platform: 'bedrock',
    provider: 'openai',
    pricing: { input: 5.5, output: 33 },
    intelligence: 8.5,
    region: '米国',
  },
  {
    value: 'openai.gpt-5.4',
    title: 'GPT-5.4',
    platform: 'bedrock',
    provider: 'openai',
    pricing: { input: 2.75, output: 16.5 },
    intelligence: 7.5,
    region: '米国',
  },
  {
    value: 'claude-sonnet-5',
    title: 'Claude Sonnet 5',
    platform: 'cpoa',
    provider: 'anthropic',
    pricing: { input: 2, output: 10 },
    pricingNote: '2026-09-01以降 $3/$15',
    intelligence: 8.5,
    region: '米国',
  },
  {
    value: 'claude-haiku-4-5',
    title: 'Claude Haiku 4.5',
    platform: 'cpoa',
    provider: 'anthropic',
    pricing: { input: 1, output: 5 },
    intelligence: 6,
    region: '米国',
  },
  {
    value: 'claude-sonnet-4-6',
    title: 'Claude Sonnet 4.6',
    platform: 'cpoa',
    provider: 'anthropic',
    pricing: { input: 3, output: 15 },
    intelligence: 7.5,
    region: '米国',
  },
]

export const DEFAULT_MODEL = 'anthropic.claude-sonnet-5'

export const TOKEN_PROFILES: Record<ModelProvider, Record<Operation, ModelPricing>> = {
  anthropic: {
    compare: { input: 3650, output: 250 },
    analyze: { input: 1900, output: 130 },
  },
  openai: {
    compare: { input: 2500, output: 300 },
    analyze: { input: 1400, output: 200 },
  },
}

export const MONITORING_COUNTS = { tenMin: 4320, oneHour: 720 }

const SONNET_5_PRICE_CHANGE = new Date('2026-09-01T00:00:00+09:00')
const SONNET_5_REGULAR_PRICING: ModelPricing = { input: 3, output: 15 }

function isSonnet5(model: ModelOption): boolean {
  return model.value === 'anthropic.claude-sonnet-5' || model.value === 'claude-sonnet-5'
}

export function effectivePricing(
  model: ModelOption,
  now: Date = new Date(),
): ModelPricing & { pricingNote?: string } {
  if (isSonnet5(model) && now >= SONNET_5_PRICE_CHANGE) {
    return { ...SONNET_5_REGULAR_PRICING }
  }

  return {
    ...model.pricing,
    ...(model.pricingNote ? { pricingNote: model.pricingNote } : {}),
  }
}

export function estimateCost(
  modelValue: string,
  operation: Operation,
  now: Date = new Date(),
): CostEstimate {
  const model = MODELS.find((item) => item.value === modelValue)
  if (!model) throw new Error(`Unknown model: ${modelValue}`)

  const pricing = effectivePricing(model, now)
  const tokens = TOKEN_PROFILES[model.provider][operation]
  const perRequestUsd = (
    tokens.input * pricing.input + tokens.output * pricing.output
  ) / 1_000_000
  const perRequestJpy = perRequestUsd * EXCHANGE_RATE_JPY
  const monthly10MinUsd = perRequestUsd * MONITORING_COUNTS.tenMin
  const monthlyHourlyUsd = perRequestUsd * MONITORING_COUNTS.oneHour

  return {
    perRequestUsd,
    perRequestJpy,
    monthly10MinUsd,
    monthly10MinJpy: monthly10MinUsd * EXCHANGE_RATE_JPY,
    monthlyHourlyUsd,
    monthlyHourlyJpy: monthlyHourlyUsd * EXCHANGE_RATE_JPY,
  }
}
