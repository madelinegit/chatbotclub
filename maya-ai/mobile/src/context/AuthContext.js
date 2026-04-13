import React, { createContext, useContext, useState, useEffect } from 'react'
import { getToken, clearToken } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getToken().then(t => {
      setToken(t)
      setLoading(false)
    })
  }, [])

  const logout = async () => {
    await clearToken()
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ token, setToken, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
