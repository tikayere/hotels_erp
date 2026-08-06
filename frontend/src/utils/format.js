// Money is always stored/transmitted as integer minor units (cents) + an
// ISO currency code (doctype_spec.md §1.2) — never a float major amount.
export function formatMoney(minor, currency) {
  if (minor == null || !currency) return '—'
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(minor / 100)
  } catch {
    return `${(minor / 100).toFixed(2)} ${currency}`
  }
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value.replace(' ', 'T')).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function nights(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0
  const ms = new Date(`${checkOut}T00:00:00`) - new Date(`${checkIn}T00:00:00`)
  return Math.max(0, Math.round(ms / 86400000))
}

const STATUS_LABELS = {
  confirmed: 'Confirmed',
  checked_in: 'Checked In',
  checked_out: 'Checked Out',
  cancelled: 'Cancelled',
  no_show: 'No-show',
  available: 'Available',
  occupied: 'Occupied',
  dirty: 'Dirty',
  clean: 'Clean',
  maintenance: 'Maintenance',
  out_of_order: 'Out of Order',
  // Housekeeping Task
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  verified: 'Verified',
  cleaning: 'Cleaning',
  inspection: 'Inspection',
  turndown: 'Turndown',
  deep_clean: 'Deep Clean',
  laundry: 'Laundry',
  // Maintenance Request
  open: 'Open',
  assigned: 'Assigned',
  resolved: 'Resolved',
  closed: 'Closed',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  urgent: 'Urgent',
  // Restaurant Order
  placed: 'Placed',
  in_kitchen: 'In Kitchen',
  served: 'Served',
  billed: 'Billed',
  // Finance Txn
  revenue: 'Revenue',
  refund: 'Refund',
  tax: 'Tax',
  expense: 'Expense',
  // HR: Staff / Leave Application / Payroll Entry
  active: 'Active',
  on_leave: 'On Leave',
  terminated: 'Terminated',
  approved: 'Approved',
  rejected: 'Rejected',
  annual: 'Annual',
  sick: 'Sick',
  unpaid: 'Unpaid',
  maternity_paternity: 'Maternity/Paternity',
  draft: 'Draft',
  processed: 'Processed',
  paid: 'Paid',
  // CRM: Guest Communication / Guest Complaint
  email: 'Email',
  phone: 'Phone',
  sms: 'SMS',
  in_person: 'In Person',
  inbound: 'Inbound',
  outbound: 'Outbound',
  room: 'Room',
  service: 'Service',
  billing: 'Billing',
  cleanliness: 'Cleanliness',
  noise: 'Noise',
  other: 'Other',
  escalated: 'Escalated',
  // Conference Booking
  tentative: 'Tentative',
  // Inventory
  linen: 'Linen',
  cleaning_supplies: 'Cleaning Supplies',
  food: 'Food',
  maintenance_supplies: 'Maintenance Supplies',
  ordered: 'Ordered',
  received: 'Received',
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}
