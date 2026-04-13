import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { AuthProvider, useAuth } from './src/context/AuthContext'
import { View, ActivityIndicator } from 'react-native'

import LoginScreen      from './src/screens/LoginScreen'
import RegisterScreen   from './src/screens/RegisterScreen'
import AgeVerifyScreen  from './src/screens/AgeVerifyScreen'
import ChatScreen       from './src/screens/ChatScreen'
import ProfileScreen    from './src/screens/ProfileScreen'

const Stack = createNativeStackNavigator()

function Navigator() {
  const { token, loading } = useAuth()

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#0a0a0b', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#c9956a" size="large" />
      </View>
    )
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!token ? (
        <>
          <Stack.Screen name="Login"    component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </>
      ) : (
        <>
          <Stack.Screen name="AgeVerify" component={AgeVerifyScreen} />
          <Stack.Screen name="Chat"      component={ChatScreen} />
          <Stack.Screen name="Profile"   component={ProfileScreen} />
        </>
      )}
    </Stack.Navigator>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <Navigator />
      </NavigationContainer>
    </AuthProvider>
  )
}
