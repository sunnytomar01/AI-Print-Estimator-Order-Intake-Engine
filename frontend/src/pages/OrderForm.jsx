import React, {useState} from 'react'
import axios from 'axios'
import StatusBadge from '../components/StatusBadge'
import PriceCard from '../components/PriceCard'

const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000')

export default function OrderForm(){
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [email, setEmail] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (e) =>{
    e.preventDefault()
    setError(null)
    setLoading(true)
    try{
      const form = new FormData()
      form.append('text', text)
      if(file) form.append('file', file)
      if(email) form.append('email', email)
      const intake = await axios.post(`${API_BASE}/intake/order`, form, {headers: {'Content-Type': 'multipart/form-data'}})
      const {order_id, raw_text} = intake.data
      const estimate = await axios.post(`${API_BASE}/estimate`, {order_id, raw_text, customer_email: email})
      setResult(estimate.data)
    }catch(err){
      console.error(err)
      const msg = err?.response?.data?.detail || err.message || 'Unknown error'
      setError(msg)
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <form onSubmit={submit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block font-medium">Order Text</label>
          <textarea className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-indigo-200 mt-2" rows={10} value={text} onChange={e=>setText(e.target.value)} placeholder="e.g. Please print 250 flyers 210x297mm C300 4/0 lamination 3 days" />

          <label className="block font-medium mt-4">Customer Email (optional)</label>
          <input className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-indigo-200 mt-2" value={email} onChange={e=>setEmail(e.target.value)} placeholder="customer@example.com" />
        </div>

        <div>
          <label className="block font-medium">Upload PDF / Image</label>
          <label className="mt-2 p-4 border-2 border-dashed rounded-lg text-center text-sm text-gray-500 flex flex-col items-center justify-center gap-2 cursor-pointer">
            <input type="file" className="hidden" onChange={e=>setFile(e.target.files[0])} />
            <div className="text-3xl">📁</div>
            <div className="font-medium">Click to upload or drag file here</div>
            <div className="text-xs text-gray-400">Support: PDF, PNG, JPG</div>
            {file && (<div className="text-sm text-gray-600 mt-2">Selected: {file.name}</div>)}
          </label>

          <div className="mt-4">
            <button className="btn-primary px-6 py-2 rounded-md" disabled={loading || (!text.trim() && !file)}>{loading? 'Processing...':'Submit'}</button>
            {(!text.trim() && !file) && (<div className="text-sm text-gray-500 mt-2">Enter text or upload a file to submit</div>)}
          </div>
        </div>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 rounded">Error: {error}</div>
      )}

      {result && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <h2 className="font-bold text-lg">Estimation</h2>
            <div className="mt-2 bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-500">Product</div>
                  <div className="font-semibold">{result.spec.product_type} — {result.spec.quantity}</div>
                  <div className="text-sm text-gray-500">{result.spec.size} • {result.spec.paper_type} • {result.spec.color}</div>
                </div>
                <div className="text-right">
                  <StatusBadge status={result.validation.decision} />
                </div>
              </div>

              <div className="mt-4">
                <pre className="bg-white p-3 rounded text-sm overflow-auto">{JSON.stringify(result.spec, null, 2)}</pre>
              </div>

              {result.validation.issues && result.validation.issues.length>0 && (
                <div className="mt-3 text-sm text-red-600">Issues: {result.validation.issues.join(', ')}</div>
              )}
            </div>
          </div>

          <div>
            <PriceCard pricing={result.pricing} />
          </div>
        </div>
      )}
    </div>
  )
}
