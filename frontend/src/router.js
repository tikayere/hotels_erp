import { createRouter, createWebHistory } from 'vue-router'
import { boot, isLoggedIn, redirectToLogin } from './session'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },
  {
    path: '/rooms',
    name: 'Rooms',
    component: () => import('@/pages/Rooms.vue'),
  },
  {
    path: '/reservations',
    name: 'Reservations',
    component: () => import('@/pages/Reservations.vue'),
  },
  {
    path: '/reservations/new',
    name: 'NewReservation',
    component: () => import('@/pages/NewReservation.vue'),
  },
  {
    path: '/reservations/:id',
    name: 'ReservationDetail',
    component: () => import('@/pages/ReservationDetail.vue'),
    props: true,
  },

  // Housekeeping
  {
    path: '/housekeeping',
    name: 'Housekeeping',
    component: () => import('@/pages/housekeeping/Board.vue'),
  },
  {
    path: '/housekeeping/:id',
    name: 'HousekeepingTaskDetail',
    component: () => import('@/pages/housekeeping/TaskDetail.vue'),
    props: true,
  },

  // Maintenance
  {
    path: '/maintenance',
    name: 'Maintenance',
    component: () => import('@/pages/maintenance/Board.vue'),
  },
  {
    path: '/maintenance/:id',
    name: 'MaintenanceRequestDetail',
    component: () => import('@/pages/maintenance/RequestDetail.vue'),
    props: true,
  },

  // Restaurant
  {
    path: '/restaurant',
    name: 'RestaurantOrders',
    component: () => import('@/pages/restaurant/Orders.vue'),
  },
  {
    path: '/restaurant/new',
    name: 'NewRestaurantOrder',
    component: () => import('@/pages/restaurant/NewOrder.vue'),
  },
  {
    path: '/restaurant/:id',
    name: 'RestaurantOrderDetail',
    component: () => import('@/pages/restaurant/OrderDetail.vue'),
    props: true,
  },

  // Finance
  {
    path: '/finance',
    name: 'Finance',
    component: () => import('@/pages/finance/Transactions.vue'),
  },

  // HR
  {
    path: '/hr/staff',
    name: 'Staff',
    component: () => import('@/pages/hr/Staff.vue'),
  },
  {
    path: '/hr/leave',
    name: 'Leave',
    component: () => import('@/pages/hr/Leave.vue'),
  },
  {
    path: '/hr/payroll',
    name: 'Payroll',
    component: () => import('@/pages/hr/Payroll.vue'),
  },

  // CRM
  {
    path: '/guests',
    name: 'Guests',
    component: () => import('@/pages/crm/Guests.vue'),
  },
  {
    path: '/guests/:id',
    name: 'GuestDetail',
    component: () => import('@/pages/crm/GuestDetail.vue'),
    props: true,
  },
  {
    path: '/complaints',
    name: 'Complaints',
    component: () => import('@/pages/crm/Complaints.vue'),
  },

  // Conference
  {
    path: '/conference',
    name: 'ConferenceBookings',
    component: () => import('@/pages/conference/Bookings.vue'),
  },
  {
    path: '/conference/new',
    name: 'NewConferenceBooking',
    component: () => import('@/pages/conference/NewBooking.vue'),
  },

  // Revenue Management
  {
    path: '/revenue',
    name: 'RatePlans',
    component: () => import('@/pages/revenue/RatePlans.vue'),
  },
  {
    path: '/revenue/:id',
    name: 'RatePlanDetail',
    component: () => import('@/pages/revenue/RatePlanDetail.vue'),
    props: true,
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('@/pages/revenue/Analytics.vue'),
  },

  // Inventory
  {
    path: '/inventory',
    name: 'InventoryItems',
    component: () => import('@/pages/inventory/Items.vue'),
  },
  {
    path: '/inventory/suppliers',
    name: 'Suppliers',
    component: () => import('@/pages/inventory/Suppliers.vue'),
  },
  {
    path: '/inventory/purchase-orders',
    name: 'PurchaseOrders',
    component: () => import('@/pages/inventory/PurchaseOrders.vue'),
  },
]

const router = createRouter({
  // Matches vite.config.js's `frontendRoute: '/pms'`.
  history: createWebHistory('/pms'),
  routes,
})

router.beforeEach((to) => {
  // Belt-and-braces: www/pms.py already redirects a Guest to /login before
  // the SPA shell is ever served, but a session can also expire while the
  // tab is already open, so re-check on every client-side navigation too.
  if (!isLoggedIn.value) {
    redirectToLogin()
    return false
  }
  if (!boot.fetched && !boot.loading) {
    boot.fetch()
  }
  return true
})

export default router
