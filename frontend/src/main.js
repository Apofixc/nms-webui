import { createApp } from 'vue'
import App from './App.vue'
import { createAppRouter } from './router'
import './style.css'

const bootstrap = async () => {
  const router = await createAppRouter()
  createApp(App).use(router).mount('#app')
}

bootstrap()
