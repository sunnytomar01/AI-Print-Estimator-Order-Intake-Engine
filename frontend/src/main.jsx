import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import OrderForm from './pages/OrderForm'

import Dashboard from './pages/Dashboard'

function App(){
  const [route, setRoute] = React.useState(window.location.hash || '#/')
  React.useEffect(()=>{
    function onHash(){ setRoute(window.location.hash || '#/') }
    window.addEventListener('hashchange', onHash)
    return ()=> window.removeEventListener('hashchange', onHash)
  },[])

  const navClass = "text-blue-600 hover:underline mr-4"

  let Page = null
  if(route === '#/dashboard') Page = <Dashboard />
  else Page = <OrderForm />

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">AI Print Estimator</h1>
          <div>
            <a className={navClass} href="#/">Order Form</a>
            <a className={navClass} href="#/dashboard">Dashboard</a>
          </div>
        </div>
        {Page}
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
