import React, { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Linking } from 'react-native'
import { verifyAge } from '../services/api'
import { colors, fonts } from '../theme'

export default function AgeVerifyScreen({ navigation }) {
  const [loading, setLoading] = useState(false)

  async function confirm() {
    setLoading(true)
    const ok = await verifyAge()
    setLoading(false)
    if (ok) navigation.replace('Chat')
  }

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.emoji}>🔞</Text>
        <Text style={styles.title}>Adults Only</Text>
        <Text style={styles.body}>
          This platform contains adult content. You must be{' '}
          <Text style={{ color: colors.textPrimary, fontWeight: '600' }}>18 years or older</Text>{' '}
          to continue. By proceeding you confirm you meet this requirement.
        </Text>

        <TouchableOpacity style={styles.btnPrimary} onPress={confirm} disabled={loading}>
          {loading
            ? <ActivityIndicator color="#0a0a0b" />
            : <Text style={styles.btnPrimaryText}>I am 18 or older — Enter</Text>}
        </TouchableOpacity>

        <TouchableOpacity style={styles.btnGhost} onPress={() => Linking.openURL('https://www.google.com')}>
          <Text style={styles.btnGhostText}>I am under 18 — Exit</Text>
        </TouchableOpacity>

        <Text style={styles.legal}>
          False confirmation may violate applicable laws.
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: colors.bgBase, justifyContent: 'center', padding: 24 },
  card:          { backgroundColor: colors.bgSurface, borderRadius: 24, padding: 32, borderWidth: 1, borderColor: colors.borderSubtle, alignItems: 'center' },
  emoji:         { fontSize: 48, marginBottom: 16 },
  title:         { fontFamily: fonts.display, fontSize: 28, color: colors.textPrimary, marginBottom: 16, textAlign: 'center' },
  body:          { fontSize: 15, color: colors.textSecondary, lineHeight: 24, textAlign: 'center', marginBottom: 32 },
  btnPrimary:    { backgroundColor: colors.accentPrimary, borderRadius: 999, padding: 15, alignItems: 'center', width: '100%', marginBottom: 12 },
  btnPrimaryText:{ color: '#0a0a0b', fontWeight: '600', fontSize: 16 },
  btnGhost:      { borderWidth: 1, borderColor: colors.borderMid, borderRadius: 999, padding: 14, alignItems: 'center', width: '100%', marginBottom: 20 },
  btnGhostText:  { color: colors.textSecondary, fontSize: 15 },
  legal:         { fontSize: 11, color: colors.textMuted, textAlign: 'center', lineHeight: 16 },
})
