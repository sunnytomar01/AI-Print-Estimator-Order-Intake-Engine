import React from 'react'

export default function PriceCard({pricing}){
  if(!pricing) return null
  return (
    <div className="p-4 bg-white rounded-xl shadow-lg border border-gray-100">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Price</h3>
        <div className="text-right">
          <div className="text-sm text-gray-500">Final</div>
          <div className="text-2xl font-bold text-gray-900">${pricing.final_price}</div>
        </div>
      </div>

      <div className="mt-4 space-y-2 text-sm text-gray-700">
        <div className="flex justify-between"><span>Process</span><span className="font-medium">{pricing.process}</span></div>
        <div className="flex justify-between"><span>Material</span><span className="font-medium">${pricing.material_cost.toFixed(2)}</span></div>
        <div className="flex justify-between"><span>Setup</span><span className="font-medium">${pricing.setup_cost.toFixed(2)}</span></div>
        <div className="flex justify-between"><span>Finishing</span><span className="font-medium">${pricing.finishing_cost.toFixed(2)}</span></div>
      </div>

      <div className="mt-4 flex gap-2">
        <button className="btn-primary w-full">Get Quote</button>
        <button className="btn-secondary">Details</button>
      </div>
    </div>
  )
}
