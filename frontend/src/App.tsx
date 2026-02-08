import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Investigation from './pages/Investigation'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/investigations/:id" element={<Investigation />} />
      </Routes>
    </BrowserRouter>
  )
}
