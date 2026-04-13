# Maya Mobile App

React Native + Expo. Same backend as the website — one deploy serves both.

---

## Local development (test on your phone today)

1. Install dependencies:
   cd mobile
   npm install

2. Set your backend URL in src/services/api.js:
   const BASE_URL = 'http://YOUR_LOCAL_IP:8000'
   (use your machine's local IP, not localhost — your phone can't reach localhost)
   Find it with: ipconfig (Windows) or ifconfig (Mac)

3. Start the dev server:
   npx expo start

4. Scan the QR code with:
   - iOS: built-in Camera app
   - Android: Expo Go app (free on Play Store)

The app opens on your phone instantly. Hot reloads on save.

---

## Building for real (EAS)

EAS compiles your app into App Store / Google Play binaries from the cloud.
You don't need Xcode or Android Studio on your machine.

### One-time setup

1. Create an Expo account at expo.dev (free)

2. Install EAS CLI:
   npm install -g eas-cli

3. Log in:
   eas login

4. Link this project to your Expo account:
   eas init
   (this fills in the projectId in app.json automatically)

5. Fill in eas.json submit section:
   - iOS: your Apple ID, App Store Connect App ID, Apple Team ID
   - Android: download a Google service account JSON from Google Play Console

---

## Build commands

### Preview build (test on real device, no app store needed)

Android APK (install directly on any Android):
   eas build --profile preview --platform android

iOS (requires Apple Developer account $99/yr):
   eas build --profile preview --platform ios

### Production build (submit to app stores)

Both platforms at once:
   eas build --profile production --platform all

---

## Submit to app stores

After a successful production build:

App Store (iOS):
   eas submit --platform ios

Google Play:
   eas submit --platform android

---

## App store requirements checklist

Before submitting you need:

iOS (Apple):
- Apple Developer account ($99/yr) at developer.apple.com
- App created in App Store Connect (appstoreconnect.apple.com)
- Privacy policy URL (use https://yourdomain.com/privacy)
- Age rating: 17+ (select this — adult content)
- App icons: already in assets/ (replace placeholders with real art)

Android (Google):
- Google Play Developer account ($25 one-time) at play.google.com/console
- App created in Play Console
- Content rating: complete the questionnaire, select Mature 17+
- Privacy policy URL

---

## Important: update BASE_URL before production build

In src/services/api.js, change:
   const BASE_URL = 'http://localhost:8000'
to your live Railway URL:
   const BASE_URL = 'https://your-app.up.railway.app'

Do this BEFORE running the production build.

---

## App store notes on adult content

Apple is strict — your app cannot contain explicit content in the App Store.
The app itself (login, chat UI) is clean. The content is server-side.
Apple has approved similar apps. Key things:
- Age gate must be prominent (it is)
- Terms of Service must be in-app (it is, linked from register screen)
- No explicit images in screenshots

Google Play is similar — submit under "Apps for adults" category.
