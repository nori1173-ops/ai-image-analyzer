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
        colors: {
          primary: '#4f46e5',
          secondary: '#f59e0b',
          success: '#059669',
          error: '#dc2626',
          warning: '#d97706',
          info: '#0891b2',
          background: '#f8fafc',
          surface: '#ffffff',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
