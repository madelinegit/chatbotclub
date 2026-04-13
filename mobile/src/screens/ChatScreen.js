import React, { useState, useEffect, useRef } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Image
} from 'react-native'
import { sendMessage, fetchCredits } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { colors, fonts } from '../theme'

export default function ChatScreen({ navigation }) {
  const { logout }          = useAuth()
  const [messages, setMessages] = useState([
    { id: '0', role: 'maya', content: 'hey. what do you want.', time: now() }
  ])
  const [input, setInput]   = useState('')
  const [typing, setTyping] = useState(false)
  const [credits, setCredits] = useState(null)
  const listRef             = useRef(null)

  useEffect(() => {
    loadCredits()
  }, [])

  async function loadCredits() {
    const data = await fetchCredits()
    setCredits(data.balance)
  }

  async function send() {
    const text = input.trim()
    if (!text) return

    const userMsg = { id: Date.now().toString(), role: 'user', content: text, time: now() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setTyping(true)

    try {
      const data = await sendMessage(text)
      setTyping(false)

      const mayaMsg = { id: Date.now().toString() + 'a', role: 'maya', content: data.reply, time: now() }
      setMessages(prev => [...prev, mayaMsg])

      if (data.followup) {
        setTyping(true)
        await delay(2000 + Math.random() * 2000)
        setTyping(false)
        const followupMsg = { id: Date.now().toString() + 'b', role: 'maya', content: data.followup, time: now() }
        setMessages(prev => [...prev, followupMsg])
      }

      loadCredits()

    } catch (err) {
      setTyping(false)
      if (err.status === 401) { logout(); return }
      if (err.status === 403) { navigation.replace('AgeVerify'); return }
      if (err.status === 402) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(), role: 'maya',
          content: "you're out of credits. go to your profile to get more.", time: now()
        }])
        return
      }
      if (err.status === 429) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(), role: 'maya',
          content: 'slow down a little.', time: now()
        }])
        return
      }
      setMessages(prev => [...prev, {
        id: Date.now().toString(), role: 'maya',
        content: 'something went wrong. try again.', time: now()
      }])
    }
  }

  function renderMessage({ item }) {
    const isMaya = item.role === 'maya'

    if (item.content.startsWith('[IMAGE]') && item.content.includes('[/IMAGE]')) {
      const url = item.content.replace('[IMAGE]', '').replace('[/IMAGE]', '').trim()
      return (
        <View style={[styles.msgRow, isMaya ? styles.msgRowMaya : styles.msgRowUser]}>
          <Image source={{ uri: url }} style={styles.msgImage} resizeMode="cover" />
          <Text style={styles.msgTime}>{item.time}</Text>
        </View>
      )
    }

    return (
      <View style={[styles.msgRow, isMaya ? styles.msgRowMaya : styles.msgRowUser]}>
        <View style={[styles.bubble, isMaya ? styles.bubbleMaya : styles.bubbleUser]}>
          <Text style={styles.bubbleText}>{item.content}</Text>
        </View>
        <Text style={[styles.msgTime, !isMaya && { textAlign: 'right' }]}>{item.time}</Text>
      </View>
    )
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.headerAvatar}><Text style={styles.headerAvatarText}>M</Text></View>
          <View>
            <Text style={styles.headerName}>Maya</Text>
            <Text style={styles.headerStatus}>● online</Text>
          </View>
        </View>
        <View style={styles.headerRight}>
          {credits !== null && (
            <View style={styles.creditsBadge}>
              <Text style={styles.creditsText}>{credits} credits</Text>
            </View>
          )}
          <TouchableOpacity onPress={() => navigation.navigate('Profile')}>
            <Text style={styles.headerLink}>Profile</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={item => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        onLayout={() => listRef.current?.scrollToEnd({ animated: false })}
      />

      {/* Typing indicator */}
      {typing && (
        <View style={styles.typingRow}>
          <View style={styles.typingBubble}>
            <Text style={styles.typingText}>Maya is typing...</Text>
          </View>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.textInput}
          value={input}
          onChangeText={setInput}
          placeholder="say something..."
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={1000}
          onSubmitEditing={send}
        />
        <TouchableOpacity style={styles.sendBtn} onPress={send}>
          <Text style={styles.sendBtnText}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

const styles = StyleSheet.create({
  container:        { flex: 1, backgroundColor: colors.bgBase },
  header:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, paddingTop: 56, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle, backgroundColor: colors.bgBase },
  headerLeft:       { flexDirection: 'row', alignItems: 'center', gap: 12 },
  headerAvatar:     { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.bgElevated, borderWidth: 1.5, borderColor: 'rgba(201,149,106,0.4)', alignItems: 'center', justifyContent: 'center' },
  headerAvatarText: { color: colors.textAccent, fontSize: 16 },
  headerName:       { color: colors.textPrimary, fontSize: 16, fontWeight: '600' },
  headerStatus:     { color: colors.accentSuccess, fontSize: 12 },
  headerRight:      { flexDirection: 'row', alignItems: 'center', gap: 12 },
  creditsBadge:     { backgroundColor: colors.bgElevated, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, borderWidth: 1, borderColor: colors.borderSubtle },
  creditsText:      { color: colors.accentPrimary, fontSize: 12, fontFamily: fonts.mono },
  headerLink:       { color: colors.textSecondary, fontSize: 14 },
  messagesList:     { padding: 16, gap: 8 },
  msgRow:           { maxWidth: '80%', marginBottom: 8 },
  msgRowMaya:       { alignSelf: 'flex-start' },
  msgRowUser:       { alignSelf: 'flex-end' },
  bubble:           { borderRadius: 18, padding: 12 },
  bubbleMaya:       { backgroundColor: '#16151a', borderWidth: 1, borderColor: 'rgba(201,149,106,0.15)', borderBottomLeftRadius: 4 },
  bubbleUser:       { backgroundColor: '#1e1c25', borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)', borderBottomRightRadius: 4 },
  bubbleText:       { color: colors.textPrimary, fontSize: 15, lineHeight: 22 },
  msgTime:          { color: colors.textMuted, fontSize: 11, marginTop: 4, paddingHorizontal: 4 },
  msgImage:         { width: 220, height: 220, borderRadius: 12 },
  typingRow:        { paddingHorizontal: 16, paddingBottom: 4 },
  typingBubble:     { backgroundColor: '#16151a', borderRadius: 14, padding: 10, alignSelf: 'flex-start', borderWidth: 1, borderColor: 'rgba(201,149,106,0.15)' },
  typingText:       { color: colors.textMuted, fontSize: 13 },
  inputRow:         { flexDirection: 'row', alignItems: 'flex-end', margin: 12, backgroundColor: colors.bgElevated, borderRadius: 24, borderWidth: 1, borderColor: colors.borderMid, paddingLeft: 16, paddingRight: 6, paddingVertical: 6 },
  textInput:        { flex: 1, color: colors.textPrimary, fontSize: 15, maxHeight: 100, paddingVertical: 6 },
  sendBtn:          { width: 36, height: 36, backgroundColor: colors.accentPrimary, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  sendBtnText:      { color: '#0a0a0b', fontSize: 18, fontWeight: '700' },
})
