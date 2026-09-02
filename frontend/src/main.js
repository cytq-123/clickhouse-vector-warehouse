import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import Overview from './views/Overview.vue'
import DWDLayer from './views/DWDLayer.vue'
import DWSLayer from './views/DWSLayer.vue'
import ADSLayer from './views/ADSLayer.vue'
import VectorLayer from './views/VectorLayer.vue'
import Architecture from './views/Architecture.vue'

const routes = [
  { path: '/', component: Overview },
  { path: '/dwd', component: DWDLayer },
  { path: '/dws', component: DWSLayer },
  { path: '/ads', component: ADSLayer },
  { path: '/vector', component: VectorLayer },
  { path: '/architecture', component: Architecture }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')