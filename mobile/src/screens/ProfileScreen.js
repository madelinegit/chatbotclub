import React, { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, Alert
} from 'react-native'
import { fetchProfile, fetchHistory, updateProfile } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { colors, fonts } from '../theme'

export default function ProfileScreen({ navigation }) {
  const { logout }                = useAuth()
  const [profile, setProfile]     = useState(null)
  const [history, setHistory]     = useState([])
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio]             = useState('')
  const [saving, setSaving]       = useState(false)
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    try {
      const [p, h] = await Promise.all([fetchProfile(), fetchHistory()])
      setProfile(p)
      setDisplayName(p.display_name || '')
      setBio(p.bio || '')
      setHistory(h.messages || [])
    } catch (err) {
      Alert.alert('Error', 'Could not load profile')
    } finally {
      setLoading(false)
    }
  }

  async function save() {
    setSaving(true)
    const ok = await updateProfile(displayName, bio)
    setSaving(false)
    if (ok) Alert.alert('Saved', 'Maya will remember this.')
    else Alert.alert('Error', 'Could not save profile')
  }

  if (loading) {
    return <View style={styles.loading}><ActivityIndicator color={colors.accentPrimary} size="large" /></View>
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scroll}>

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={logout}>
          <Text style={styles.logoutBtn}>Log out</Text>
        </TouchableOpacity>
      </View>

      {/* Avatar + name */}
      <View style={styles.avatarRow}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{displayName ? displayName[0].toUpperCase() : '?'}</Text>
        </View>
        <View>
          <Text style={styles.userName}>{displayName || 'Your Profile'}</Text>
          <Text style={styles.userEmail}>{profile?.email}</Text>
        </View>
      </View>

      {/* Credits */}
      <View style={styles.creditsCard}>
        <View>
          <Text style={styles.creditsLabel}>Credit Balance</Text>
          <Text style={styles.creditsValue}>{profile?.credits ?? 0}</Text>
        </View>
        <TouchableOpacity style={styles.btnPrimary} onPress={() => navigation.navigate('Chat')}>
          <Text style={styles.btnPrimaryText}>+ Get Credits</Text>
        </TouchableOpacity>
      </View>

      {/* Profile form */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>About You</Text>
        <Text style={styles.cardSubtitle}>
          Maya reads this before every conversation. Tell her your name, what you're into,
          how you want her to treat you.
        </Text>

        <Text style={styles.label}>What should Maya call you?</Text>
        <TextInput
          style={styles.input}
          value={displayName}
          onChangeText={setDisplayName}
          placeholder="your name or nickname"
          placeholderTextColor={colors.textMuted}
          maxLength={50}
        />

        <Text style={styles.label}>Tell Maya about yourself</Text>
        <TextInput
          style={[styles.input, styles.textarea]}
          value={bio}
          onChangeText={setBio}
          placeholder="What are you into? How do you want her to talk to you? The more you share, the better she knows you."
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={1000}
        />
        <Text style={styles.charCount}>{bio.length}/1000</Text>

        <TouchableOpacity style={styles.btnPrimary} onPress={save} disabled={saving}>
          {saving
            ? <ActivityIndicator color="#0a0a0b" />
            : <Text style={styles.btnPrimaryText}>Save Profile</Text>}
        </TouchableOpacity>
      </View>

      {/* Chat History */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Chat History</Text>
        <Text style={styles.cardSubtitle}>{history.length} messages</Text>

        {history.slice(-30).map((msg, i) => (
          <View key={i} style={styles.historyItem}>
            <Text style={[styles.historyRole, msg.role === 'maya' && { color: colors.textAccent }]}>
              {msg.role === 'user' ? 'You' : 'Maya'}
            </Text>
            <Text style={styles.historyContent} numberOfLines={2}>{msg.content}</Text>
          </View>
        ))}

        {history.length === 0 && (
          <Text style={styles.cardSubtitle}>No messages yet.</Text>
        )}
      </View>

    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: colors.bgBase },
  scroll:        { padding: 20, paddingBottom: 60 },
  loading:       { flex: 1, backgroundColor: colors.bgBase, alignItems: 'center', justifyContent: 'center' },
  header:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 48, marginBottom: 28 },
  backBtn:       { color: colors.accentPrimary, fontSize: 16 },
  logoutBtn:     { color: colors.textMuted, fontSize: 14 },
  avatarRow:     { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 24 },
  avatar:        { width: 72, height: 72, borderRadius: 36, backgroundColor: colors.bgElevated, borderWidth: 2, borderColor: 'rgba(201,149,106,0.4)', alignItems: 'center', justifyContent: 'center' },
  avatarText:    { color: colors.textAccent, fontSize: 28 },
  userName:      { color: colors.textPrimary, fontSize: 20, fontWeight: '600', marginBottom: 4 },
  userEmail:     { color: colors.textMuted, fontSize: 13 },
  creditsCard:   { backgroundColor: colors.bgSurface, borderRadius: 16, padding: 20, borderWidth: 1, borderColor: 'rgba(201,149,106,0.25)', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 },
  creditsLabel:  { color: colors.textMuted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 },
  creditsValue:  { color: colors.accentPrimary, fontSize: 28, fontFamily: fonts.mono },
  card:          { backgroundColor: colors.bgSurface, borderRadius: 16, padding: 20, borderWidth: 1, borderColor: colors.borderSubtle, marginBottom: 20 },
  cardTitle:     { color: colors.textPrimary, fontSize: 18, fontWeight: '600', marginBottom: 6 },
  cardSubtitle:  { color: colors.textMuted, fontSize: 13, lineHeight: 20, marginBottom: 20 },
  label:         { fontSize: 11, color: colors.textSecondary, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6, fontWeight: '500' },
  input:         { backgroundColor: colors.bgElevated, color: colors.textPrimary, borderWidth: 1, borderColor: colors.borderMid, borderRadius: 12, padding: 13, fontSize: 15, marginBottom: 16 },
  textarea:      { height: 120, textAlignVertical: 'top' },
  charCount:     { color: colors.textMuted, fontSize: 11, textAlign: 'right', marginTop: -12, marginBottom: 16 },
  btnPrimary:    { backgroundColor: colors.accentPrimary, borderRadius: 999, padding: 14, alignItems: 'center' },
  btnPrimaryText:{ color: '#0a0a0b', fontWeight: '600', fontSize: 15 },
  historyItem:   { flexDirection: 'row', gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle },
  historyRole:   { color: colors.textMuted, fontSize: 12, width: 36, paddingTop: 2, fontFamily: fonts.mono },
  historyContent:{ flex: 1, color: colors.textSecondary, fontSize: 13, lineHeight: 20 },
})
