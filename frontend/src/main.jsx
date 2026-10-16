import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { ThemeProvider } from './theme/ThemeContext'
import { cssText } from './theme/themes'
import './index.css'

// Colour tokens of both themes as CSS variables (single source: src/theme/themes.js).
const style = document.createElement('style')
style.id = 'theme-tokens'
style.textContent = cssText()
document.head.appendChild(style)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)
