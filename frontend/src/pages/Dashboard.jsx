import React, {useEffect, useState} from 'react'
import axios from 'axios'
import StatusBadge from '../components/StatusBadge'

const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000')

export default function Dashboard(){
  const [summary, setSummary] = useState(null)
  const [orders, setOrders] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(()=>{
    setLoading(true)
    Promise.all([
      axios.get(`${API_BASE}/dashboard/summary`).then(r=>r.data),
      axios.get(`${API_BASE}/dashboard/orders`).then(r=>r.data),
      axios.get(`${API_BASE}/dashboard/stats`).then(r=>r.data)
    ]).then(([s, o, st])=>{
      setSummary(s)
      setOrders(o)
      setStats(st)
    }).catch(e=>{
      setError(e.message)
    }).finally(()=>setLoading(false))
  },[])

  return (
    <div className="bg-white p-6 rounded shadow">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      {loading && <div className="mt-3 text-sm text-gray-500">Loading...</div>}
      {error && <div className="mt-3 text-red-600">{error}</div>}

      {summary && (
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 rounded">
            <div className="text-sm text-gray-500">Total Orders</div>
            <div className="text-2xl font-bold">{summary.total_orders}</div>
          </div>
          <div className="p-4 bg-gray-50 rounded">
            <div className="text-sm text-gray-500">Revenue</div>
            <div className="text-2xl font-bold">${summary.revenue.toFixed(2)}</div>
          </div>
          <div className="p-4 bg-gray-50 rounded">
            <div className="text-sm text-gray-500">Pending Reviews</div>
            <div className="text-2xl font-bold">{summary.pending}</div>
          </div>
        </div>
      )}

      <div className="mt-6">
        <h3 className="font-semibold">Stats</h3>
        {stats && (
          <div className="mt-2 bg-white p-4 rounded border">
            {Object.entries(stats.by_status || {}).map(([k,v])=> (
              <div key={k} className="flex justify-between py-1"><div className="text-sm text-gray-700">{k}</div><div className="font-medium">{v}</div></div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6">
        <h3 className="font-semibold">Recent Orders</h3>
        <div className="mt-2 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-gray-50"><tr><th className="p-2">ID</th><th className="p-2">Product</th><th className="p-2">Qty</th><th className="p-2">Status</th><th className="p-2">Price</th><th className="p-2">Email</th><th className="p-2">Issues</th></tr></thead>
            <tbody>
              {orders.slice().reverse().slice(0,50).map(o=> (
                <tr key={o.id} className="border-b"><td className="p-2">{o.id}</td><td className="p-2">{o.product_type||'—'}</td><td className="p-2">{o.quantity||'—'}</td><td className="p-2"><StatusBadge status={o.status} /></td><td className="p-2">{o.final_price!=null?('$'+o.final_price):'—'}</td><td className="p-2">{o.email||'—'}</td><td className="p-2">{o.issues||''}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
