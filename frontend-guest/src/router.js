import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/rooms',
    name: 'Rooms',
    component: () => import('@/pages/Rooms.vue'),
  },
  {
    path: '/book',
    name: 'Book',
    component: () => import('@/pages/Book.vue'),
  },
  {
    path: '/confirmation/:confirmationNumber',
    name: 'Confirmation',
    component: () => import('@/pages/Confirmation.vue'),
    props: true,
  },
  {
    path: '/lookup',
    name: 'Lookup',
    component: () => import('@/pages/Lookup.vue'),
  },
]

const router = createRouter({
  // Matches vite.config.js's `frontendRoute: '/book'` (same convention as
  // erp/frontend/src/router.js's createWebHistory('/pms')).
  history: createWebHistory('/book'),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
