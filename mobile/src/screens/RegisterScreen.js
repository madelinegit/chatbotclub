import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Alert, ScrollView
} from 'react-native'
import { register } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { colors, fonts } from '../theme'

export default function RegisterScreen({ navigation }) {
  const { setToken }            = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleRegister() {
    if (!email || !password || !confirm) { Alert.alert('Fill in all fields'); return }
    if (password.length < 8) { Alert.alert('Password must be at least 8 characters'); return }
    if (password !== confirm) { Alert.alert('Passwords do not match'); return }

    setLoading(true)
    try {
      const data = await register(email.trim(), password)
      setToken(data.access_token)
    } catch (err) {
      Alert.alert('Registration Failed', err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.logo}>Maya</Text>
          <Text style={styles.tagline}>create your account</Text>

          <Text style={styles.label}>Email</Text>
          <TextInput style={styles.input} value={email} onChangeText={setEmail}
            placeholder="you@example.com" placeholderTextColor={colors.textMuted}
            keyboardType="email-address" autoCapitalize="none" />

          <Text style={styles.label}>Password</Text>
          <TextInput style={styles.input} value={password} onChangeText={setPassword}
            placeholder="at least 8 characters" placeholderTextColor={colors.textMuted}
            secureTextEntry />

          <Text style={styles.label}>Confirm Password</Text>
          <TextInput style={styles.input} value={confirm} onChangeText={setConfirm}
            placeholder="••••••••" placeholderTextColor={colors.textMuted}
            secureTextEntry onSubmitEditing={handleRegister} />

          <TouchableOpacity style={styles.btnPrimary} onPress={handleRegister} disabled={loading}>
            {loading
              ? <ActivityIndicator color="#0a0a0b" />
              : <Text style={styles.btnPrimaryText}>Create Account</Text>}
          </TouchableOpacity>

          <Text style={styles.legal}>
            By creating an account you confirm you are 18 or older and agree to our Terms of Service.
          </Text>

          <View style={styles.footer}>
            <Text style={styles.footerText}>Already have an account? </Text>
            <TouchableOpacity onPress={() => navigation.navigate('Login')}>
              <Text style={styles.link}>Sign in</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: colors.bgBase },
  scroll:        { flexGrow: 1, justifyContent: 'center', padding: 24 },
  card:          { backgroundColor: colors.bgSurface, borderRadius: 24, padding: 32, borderWidth: 1, borderColor: colors.borderSubtle },
  logo:          { fontFamily: fonts.display, fontSize: 36, color: colors.textAccent, textAlign: 'center', marginBottom: 4 },
  tagline:       { fontSize: 11, color: colors.textMuted, textAlign: 'center', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 32 },
  label:         { fontSize: 11, color: colors.textSecondary, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6, fontWeight: '500' },
  input:         { backgroundColor: colors.bgElevated, color: colors.textPrimary, borderWidth: 1, borderColor: colors.borderMid, borderRadius: 12, padding: 13, fontSize: 15, marginBottom: 16 },
  btnPrimary:    { backgroundColor: colors.accentPrimary, borderRadius: 999, padding: 15, alignItems: 'center', marginTop: 8, marginBottom: 16 },
  btnPrimaryText:{ color: '#0a0a0b', fontWeight: '600', fontSize: 16 },
  legal:         { fontSize: 12, color: colors.textMuted, textAlign: 'center', lineHeight: 18, marginBottom: 20 },
  footer:        { flexDirection: 'row', justifyContent: 'center' },
  footerText:    { color: colors.textMuted, fontSize: 14 },
  link:          { color: colors.accentPrimary, fontSize: 14 },
})
