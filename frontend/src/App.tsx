import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Globe from './pages/Globe'
import Stocks from './pages/Stocks'
import StockDetail from './pages/StockDetail'
import Model from './pages/Model'
//most of them not done yet but good to keep structure idea

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main style={{ paddingTop: 'var(--navbar-h)' }}>
        <Routes>
          <Route path="/"              element={<Landing />} />
          <Route path="/globe"         element={<Globe />} />
          <Route path="/stocks"        element={<Stocks />} />
          <Route path="/stocks/:ticker" element={<StockDetail />} />
          <Route path="/model"         element={<Model />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}