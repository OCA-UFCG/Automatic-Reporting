import { createElement, StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Laboratorio from './Laboratorio.jsx'
import './laboratorio.css'

createRoot(document.getElementById('root')).render(
  createElement(StrictMode, null, createElement(Laboratorio))
)
