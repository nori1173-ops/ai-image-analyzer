import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { DEFAULT_MODEL, MODELS } from '../models'

vi.mock('aws-amplify', () => ({
  Amplify: { configure: vi.fn() },
}))

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { idToken: { toString: () => 'mock-token' } },
  }),
}))

vi.mock('@aws-amplify/ui-vue', () => ({
  Authenticator: {
    name: 'Authenticator',
    template: '<div class="auth-mock"><slot :user="{ username: \'demouser\' }" :signOut="() => {}" /></div>',
  },
}))

vi.mock('../amplifyconfiguration', () => ({
  default: {
    Auth: {
      Cognito: {
        userPoolId: 'test-pool-id',
        userPoolClientId: 'test-client-id',
      },
    },
  },
}))

const vuetify = createVuetify({ components, directives })

describe('App', () => {
  it('BedrockとClaude Platform on AWSの12モデルを表示し、Bedrock Sonnet 5を既定にする', () => {
    expect(MODELS.map((model) => model.value)).toEqual([
      'anthropic.claude-sonnet-5',
      'anthropic.claude-haiku-4-5',
      'anthropic.claude-opus-4-7',
      'anthropic.claude-opus-4-8',
      'openai.gpt-5.6-terra',
      'openai.gpt-5.6-luna',
      'openai.gpt-5.6-sol',
      'openai.gpt-5.5',
      'openai.gpt-5.4',
      'claude-sonnet-5',
      'claude-haiku-4-5',
      'claude-sonnet-4-6',
    ])
    expect(MODELS).toHaveLength(12)
    expect(DEFAULT_MODEL).toBe('anthropic.claude-sonnet-5')
  })

  it('renders without crashing', async () => {
    const { default: App } = await import('../App.vue')
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('解析リクエストにdetailを含めない', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ found: true, confidence: 100 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { default: App } = await import('../App.vue')
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    const uploader = wrapper.findAllComponents({ name: 'ImageUploader' })[0]!
    await uploader.vm.$emit('update', 'data:image/png;base64,image', 'preview')
    await wrapper.findComponent({ name: 'AnalysisForm' }).vm.$emit('analyze', {
      target: 'ひび割れ',
      model: 'claude-haiku-4-5',
      detail: 'auto',
    })

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    const request = fetchMock.mock.calls[0]![1] as RequestInit
    expect(JSON.parse(request.body as string)).not.toHaveProperty('detail')
    vi.unstubAllGlobals()
  })

  it('比較リクエストにdetailを含めない', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ danger: false, risk_level: 'none' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { default: App } = await import('../App.vue')
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    const compareTab = wrapper.findAll('[role="tab"]').find((tab) => tab.text().includes('画像比較'))
    await compareTab!.trigger('click')
    await wrapper.vm.$nextTick()

    const uploaders = wrapper.findAllComponents({ name: 'ImageUploader' })
    await uploaders[1]!.vm.$emit('update', 'data:image/png;base64,before')
    await uploaders[2]!.vm.$emit('update', 'data:image/png;base64,after')
    await wrapper.findComponent({ name: 'CompareForm' }).vm.$emit('compare', {
      perspective: '河川水位の上昇',
      model: 'claude-haiku-4-5',
      detail: 'high',
      notify: false,
      notifyTo: '',
      notifyCc: '',
      notifyBcc: '',
      notifyLine: false,
    })

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    const request = fetchMock.mock.calls[0]![1] as RequestInit
    expect(JSON.parse(request.body as string)).not.toHaveProperty('detail')
    vi.unstubAllGlobals()
  })
})
