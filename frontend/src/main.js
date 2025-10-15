import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import AssessmentView from './views/AssessmentView.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: AssessmentView
    }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')
