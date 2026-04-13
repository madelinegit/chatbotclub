import * as SecureStore from 'expo-secure-store'

// !! Change this to your deployed URL when live !!
const BASE_URL = 'https://magicmaya.vip'

export async function getToken() {
  return await SecureStore.getItemAsync('maya_token')
}

export async function saveToken(token) {
  await SecureStore.setItemAsync('maya_token', token)
}

export async function clearToken() {
  await SecureStore.deleteItemAsync('maya_token')
}

export async function authFetch(path, options = {}) {
  const token = await getToken()
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  })
}

export async function login(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Login failed')
  await saveToken(data.access_token)
  return data
}

export async function register(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Registration failed')
  await saveToken(data.access_token)
  return data
}

export async function sendMessage(message) {
  const res = await authFetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
  const data = await res.json()
  if (!res.ok) throw { status: res.status, detail: data.detail }
  return data
}

export async function fetchProfile() {
  const res = await authFetch('/api/profile/me')
  if (!res.ok) throw new Error('Failed to load profile')
  return res.json()
}

export async function fetchHistory() {
  const res = await authFetch('/api/profile/history')
  if (!res.ok) throw new Error('Failed to load history')
  return res.json()
}

export async function fetchCredits() {
  const res = await authFetch('/api/payments/balance')
  if (!res.ok) return { balance: 0 }
  return res.json()
}

export async function verifyAge() {
  const res = await authFetch('/api/profile/verify-age', { method: 'POST' })
  return res.ok
}

export async function updateProfile(displayName, bio) {
  const formData = new FormData()
  if (displayName) formData.append('display_name', displayName)
  if (bio) formData.append('bio', bio)
  const token = await getToken()
  const res = await fetch(`${BASE_URL}/api/profile/update`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  })
  return res.ok
}
