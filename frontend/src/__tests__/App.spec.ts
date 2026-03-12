import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

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
  it('renders without crashing', async () => {
    const { default: App } = await import('../App.vue')
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })
    expect(wrapper.exists()).toBe(true)
  })
})
