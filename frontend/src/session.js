// Session state for the Front Desk SPA.
//
// `user` is read from the `user_id` cookie Frappe's session sets on every
// request (not from the one-time boot payload) so it stays correct both on
// first load *and* right after an in-app login/logout round-trip, without a
// full page reload — same trick frappe/crm's session store uses.
import { computed, ref } from 'vue'
import { createResource } from 'frappe-ui'

function sessionUser() {
  const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  const value = cookies.get('user_id')
  return value && value !== 'Guest' ? decodeURIComponent(value) : null
}

export const user = ref(sessionUser())
export const isLoggedIn = computed(() => !!user.value)

export function redirectToLogin() {
  const redirectTo = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/login?redirect-to=${redirectTo}`
}

// hotel_erp.api.pms.get_boot_info — current user's full name, roles and the
// property list, fetched once when the shell mounts.
export const boot = createResource({
  url: 'hotel_erp.api.pms.get_boot_info',
  auto: false,
  onError(error) {
    // A 403 here almost always means the session cookie expired mid-visit
    // (the initial page load already gates Guests server-side in www/pms.py)
    // — bounce to login rather than show a broken, half-loaded screen.
    if (error?.exc_type === 'AuthenticationError' || error?.httpStatus === 403) {
      redirectToLogin()
    }
  },
})

export const logoutResource = createResource({
  url: 'logout',
  onSuccess() {
    user.value = null
    window.location.href = '/login?redirect-to=/pms'
  },
})

export function logout() {
  logoutResource.submit()
}
