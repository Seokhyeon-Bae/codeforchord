import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createAuth0 } from '@auth0/auth0-vue'
import App from './App.vue'
import './style.css'

const app = createApp(App)

console.log('AUTH0_DOMAIN:', import.meta.env.VITE_AUTH0_DOMAIN)
console.log('AUTH0_CLIENT_ID:', import.meta.env.VITE_AUTH0_CLIENT_ID)

app.use(createPinia())

app.use(
  createAuth0({
    domain: import.meta.env.VITE_AUTH0_DOMAIN,
    clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
    authorizationParams: {
      redirect_uri: window.location.origin,
      audience: import.meta.env.VITE_AUTH0_AUDIENCE,
    },
  })
)

app.mount('#app')
