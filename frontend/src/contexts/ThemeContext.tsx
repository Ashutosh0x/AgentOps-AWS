import React, { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage first, then system preference
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme') as Theme
      if (saved === 'dark' || saved === 'light') {
        return saved
      }
      
      // Check system preference
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark'
      }
    }
    return 'light'
  })

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const root = window.document.documentElement
      
      // Remove dark class first
      root.classList.remove('dark')
      
      // Add the current theme class
      if (theme === 'dark') {
        root.classList.add('dark')
      }
      
      // Also set data attribute for debugging
      root.setAttribute('data-theme', theme)
      
      // Save to localStorage
      localStorage.setItem('theme', theme)
    }
  }, [theme])

  const toggleTheme = () => {
    console.log('Toggling theme from:', theme)
    setTheme((prev) => {
      const newTheme = prev === 'light' ? 'dark' : 'light'
      console.log('New theme:', newTheme)
      return newTheme
    })
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

