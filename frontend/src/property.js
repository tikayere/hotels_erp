// The property (hotel) filter selected in the top bar, shared across every
// page (Dashboard/Rooms/Reservations/New Reservation all scope their data to
// it). Persisted in localStorage so a reload keeps the front-desk agent on
// the property they were working, rather than resetting to "All".
import { ref, watch } from 'vue'

const STORAGE_KEY = 'hotel_erp:pms:active_property'

export const activeProperty = ref(localStorage.getItem(STORAGE_KEY) || '')

watch(activeProperty, (value) => {
  if (value) {
    localStorage.setItem(STORAGE_KEY, value)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
})
