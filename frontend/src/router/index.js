import { createRouter, createWebHistory } from 'vue-router'
import AssessmentView from '../views/AssessmentView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'assessment',
      component: AssessmentView
    }
  ]
})

export default router