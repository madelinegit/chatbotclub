import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Alert
} from 'react-native'
import { login } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { colors, fonts } from '../theme'

export default function LoginScreen({ navigation }) {
  const { setToken } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleLogin() {
    if (!email || !password) { Alert.alert('Fill in all fields'); return }
    setLoading(true)
    try {
      const data = await login(email.trim(), password)
      setToken(data.access_token)
    } catch (err) {
      Alert.alert('Login Failed', err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <View style={styles.card}>
        <Text style={styles.logo}>Maya</Text>
        <Text style={styles.tagline}>sign in to continue</Text>

        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          placeholderTextColor={colors.textMuted}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          onSubmitEditing={handleLogin}
        />

        <TouchableOpacity style={styles.btnPrimary} onPress={handleLogin} disabled={loading}>
          {loading
            ? <ActivityIndicator color="#0a0a0b" />
            : <Text style={styles.btnPrimaryText}>Sign In</Text>}
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Don't have an account? </Text>
          <TouchableOpacity onPress={() => navigation.navigate('Register')}>
            <Text style={styles.link}>Create one</Text>
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: colors.bgBase, justifyContent: 'center', padding: 24 },
  card:          { backgroundColor: colors.bgSurface, borderRadius: 24, padding: 32, borderWidth: 1, borderColor: colors.borderSubtle },
  logo:          { fontFamily: fonts.display, fontSize: 36, color: colors.textAccent, textAlign: 'center', marginBottom: 4 },
  tagline:       { fontSize: 11, color: colors.textMuted, textAlign: 'center', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 32 },
  label:         { fontSize: 11, color: colors.textSecondary, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6, fontWeight: '500' },
  input:         { backgroundColor: colors.bgElevated, color: colors.textPrimary, borderWidth: 1, borderColor: colors.borderMid, borderRadius: 12, padding: 13, fontSize: 15, marginBottom: 16 },
  btnPrimary:    { backgroundColor: colors.accentPrimary, borderRadius: 999, padding: 15, alignItems: 'center', marginTop: 8, marginBottom: 20 },
  btnPrimaryText:{ color: '#0a0a0b', fontWeight: '600', fontSize: 16 },
  footer:        { flexDirection: 'row', justifyContent: 'center' },
  footerText:    { color: colors.textMuted, fontSize: 14 },
  link:          { color: colors.accentPrimary, fontSize: 14 },
})
