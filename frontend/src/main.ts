import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import { Amplify } from 'aws-amplify'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import amplifyConfig from './amplifyconfiguration'
import './style.css'

Amplify.configure(amplifyConfig)

const vuetify = createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        variables: {
          'overlay-multiplier': 1,
        },
        colors: {
          primary: '#1976d2',
          secondary: '#0097a7',
          success: '#2e7d32',
          error: '#d32f2f',
          background: '#e1f5fe',
          surface: '#ffffff',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
