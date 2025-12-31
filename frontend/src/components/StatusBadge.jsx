import React from 'react'

export default function StatusBadge({status}){
  const map = {
    auto_approved: 'bg-green-50 text-green-800',
    needs_review: 'bg-yellow-50 text-yellow-800',
    rejected: 'bg-red-50 text-red-800',
    received: 'bg-blue-50 text-blue-800'
  }
  const cls = map[status] || 'bg-gray-50 text-gray-800'
  return <span className={`inline-flex items-center gap-2 px-3 py-1 text-xs font-semibold rounded-full shadow-sm ${cls}`}>{status.replace('_',' ').toUpperCase()}</span>
}
