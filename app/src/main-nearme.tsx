import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import NearMe from './pages/NearMe'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><NearMe /></StrictMode>
)
