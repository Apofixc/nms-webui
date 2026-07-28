import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { createAppRouter } from './core/router'
import './style.css'

const bootstrap = async () => {
    const pinia = createPinia()
    const router = await createAppRouter()
    createApp(App).use(pinia).use(router).mount('#app')
}

bootstrap()
