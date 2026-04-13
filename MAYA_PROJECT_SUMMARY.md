# Maya AI — Project Summary
*Session documented: April 2026*
*Domain: magicmaya.vip*
*GitHub: https://github.com/madelinegit/maya*

---

## What Was Built This Session

A complete rewrite of the Maya AI chatbot from a prototype into a scalable,
monetizable product with user auth, persistent memory, credit payments, age
verification, user profiles, a landing page, admin dashboard, social media
automation, local awareness, and a React Native mobile app.

---

## Tech Stack — Final Decisions

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI (Python) | Async, API-first, scales cleanly |
| Auth | Supabase | Managed auth, free tier, 50k MAU |
| Database | SQLite → Postgres | SQLite for dev/launch, migrate later |
| Payments | CCBill | Adult-friendly, revenue share only, no monthly fee |
| Image Generation | ModelsLab SDXL (dev) → LoRA (prod) | Placeholder now, consistent character model needed |
| Deployment | Railway | Simple FastAPI deploy, free to start |
| Mobile | React Native + Expo | iOS + Android from one codebase |
| Social | X (Twitter) via Tweepy | Instagram stubbed, ready to wire |
| Local News | RSS + Open-Meteo | Free, no API keys required |
| Domain | magicmaya.vip | Confirmed |

---

## Full Project Structure

```
maya-ai/
├── app/
│   ├── main.py                        — app init, all page routes
│   ├── config.py                      — all env vars, DEV_MODE flag
│   │
│   ├── ai/
│   │   ├── chat.py                    — orchestration, persona + user profile + local context
│   │   ├── image.py                   — ModelsLab image generation
│   │   ├── memory.py                  — DB-backed conversation history
│   │   └── persona.py                 — loads persona/maya.txt
│   │
│   ├── api/
│   │   ├── chat_routes.py             — /api/chat with age gate, rate limit, credit check
│   │   ├── auth_routes.py             — /api/auth/login, /register
│   │   ├── payment_routes.py          — /api/payments/balance, /packages, /purchase, /webhook/ccbill
│   │   ├── profile_routes.py          — /api/profile/me, /update, /history, /transactions, /verify-age
│   │   └── admin_routes.py            — /admin/* all admin API endpoints
│   │
│   ├── db/
│   │   ├── database.py                — SQLite connection + table creation on startup
│   │   └── crud.py                    — all query functions for all tables
│   │
│   ├── models/
│   │   └── schemas.py                 — Pydantic request/response models
│   │
│   └── services/
│       ├── auth_service.py            — Supabase auth, 10 free credits on signup
│       ├── payment_service.py         — CCBill placeholder + package definitions
│       ├── rate_limiter.py            — 30 messages/minute per user, sliding window
│       ├── social_service.py          — LLM post generation + X posting (tweepy lazy import)
│       └── local_context_service.py   — RSS news + Open-Meteo snow conditions
│
├── mobile/                            — React Native (Expo) app
│   ├── App.js                         — navigation stack, auth-aware routing
│   ├── package.json
│   ├── README.md
│   └── src/
│       ├── context/AuthContext.js     — token storage, logout
│       ├── services/api.js            — all API calls, BASE_URL = https://magicmaya.vip
│       └── screens/
│           ├── LoginScreen.js         — login + register combined
│           ├── AgeVerifyScreen.js     — 18+ gate
│           ├── ChatScreen.js          — full chat, typing indicator, image support, credits
│           └── ProfileScreen.js       — avatar, bio, chat history, credits, logout
│
├── persona/
│   └── maya.txt                       — Maya's full personality definition
│
├── static/
│   ├── style.css                      — full design system, dark editorial aesthetic
│   ├── app.js                         — chat frontend logic, auth, credits, paywall
│   └── avatars/                       — user avatar uploads (auto-created at runtime)
│
├── templates/
│   ├── landing.html                   — public landing page at /
│   ├── chat.html                      — main chat UI at /chat
│   ├── login.html                     — login page
│   ├── register.html                  — register + 18+ confirmation
│   ├── age_verify.html                — age gate, redirects to /chat on confirm
│   ├── profile.html                   — avatar upload, bio, chat history, credits
│   ├── terms.html                     — Terms of Service (required for CCBill)
│   ├── privacy.html                   — Privacy Policy
│   ├── admin_login.html               — admin-only login page at /admin
│   ├── admin_dashboard.html           — full admin dashboard at /admin/dashboard
│   └── admin.html                     — legacy (can be deleted)
│
├── data/
│   └── .gitkeep                       — DB auto-created on first run, never committed
│
├── scheduler.py                       — runs separately, generates social posts on schedule
├── .env.example                       — all env var template
├── .gitignore
└── requirements.txt
```

---

## Database Schema

```sql
users           — id, email, created_at, is_active, age_verified
user_profiles   — user_id, display_name, bio, avatar_url, updated_at
sessions        — id, user_id, created_at, expires_at
messages        — id, user_id, role, content, created_at
credits         — user_id, balance, updated_at
transactions    — id, user_id, amount_cents, credits_added, processor_ref, created_at
social_posts    — id, platform, caption, image_url, image_prompt, status, post_id,
                  scheduled_at, posted_at, created_at
```

---

## All Page Routes

| URL | Who sees it | What it is |
|---|---|---|
| / | Public | Landing page |
| /chat | Logged-in users | Main chat interface |
| /login | Public | Login page |
| /register | Public | Register + age confirmation |
| /age-verify | Logged-in, unverified | 18+ gate |
| /profile | Logged-in users | Profile, bio, history, credits |
| /terms | Public | Terms of Service |
| /privacy | Public | Privacy Policy |
| /admin | You only | Admin login |
| /admin/dashboard | You only | Full admin dashboard |

---

## All API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | None | Create account |
| POST | /api/auth/login | None | Login, returns token |
| POST | /api/chat | Bearer token | Send message, costs 1 credit |
| GET | /api/payments/packages | None | List credit packages |
| GET | /api/payments/balance | Bearer token | Get credit balance |
| POST | /api/payments/purchase | Bearer token | Get CCBill payment URL |
| POST | /api/payments/webhook/ccbill | None | CCBill payment webhook |
| GET | /api/profile/me | Bearer token | Get profile + credits |
| POST | /api/profile/update | Bearer token | Update name, bio, avatar |
| GET | /api/profile/history | Bearer token | Full chat history |
| GET | /api/profile/transactions | Bearer token | Transaction history |
| POST | /api/profile/verify-age | Bearer token | Confirm 18+ |
| GET | /admin/posts | Admin secret | List posts |
| POST | /admin/posts/{id}/approve | Admin secret | Approve post |
| POST | /admin/posts/{id}/reject | Admin secret | Reject post |
| POST | /admin/posts/{id}/post-now | Admin secret | Post to X immediately |
| POST | /admin/generate | Admin secret | Generate new post now |
| GET | /admin/stats | Admin secret | Dashboard stats |
| GET | /admin/users | Admin secret | All users list |
| GET | /admin/local-context | Admin secret | Preview local news/conditions |

---

## Credit Pricing

| Package | Credits | Price | Per message | Notes |
|---|---|---|---|---|
| Starter | 50 | $7.99 | $0.16 | Low commitment, easy yes |
| Popular ⭐ | 150 | $19.99 | $0.13 | Most revenue comes from here |
| Premium | 400 | $44.99 | $0.11 | Whales and regulars |

New users get **10 free credits** on signup. No subscription required.
CCBill takes ~12%. No monthly platform fee.

---

## Branding

**Palette:** Black (#0a0a0b) base, terracotta (#c9956a) accent, gold (#e8c8a0) text.
All in style.css as CSS variables.

**Typography:**
- Display / Logo: DM Serif Display, italic
- Body / UI: DM Sans
- Numbers / Mono: JetBrains Mono

**Logo directions (all approved):**
- **Option A** — Italic serif "Maya" wordmark. Use in nav + site header.
- **Option B** — M monogram in terracotta circle. Use as app icon + favicon.
- **Option C** — Wordmark + thin rule + "PREMIUM AI" small caps. Use in marketing.

**Voice:** intimate, editorial, dangerous, premium, real.
NOT: cute, pink, bubbly, neon, corporate, anime.

---

## DEV MODE

Set `DEV_MODE=true` in `.env` to bypass credits and age gate locally.
Never set in production — defaults to `false`.

Add test credits manually:
```bash
sqlite3 data/maya.db "UPDATE credits SET balance=999 WHERE user_id='your-id';"
```

---

## Admin Dashboard

**URL:** `https://magicmaya.vip/admin`
Enter your `ADMIN_SECRET` to log in. Bookmark the dashboard URL — keep it private.

**Tabs:**
- **Posts** — review pending social posts, approve/reject/post-now. Stats at top.
- **Users** — every account with email, credits, age verification status, message count.
- **Local Context** — live preview of what news + conditions Maya is currently aware of.

**Admin login looks completely different from the user site** — dark, minimal,
system font, no branding, no connection to the user-facing design.

---

## Local Awareness

`app/services/local_context_service.py` fetches in real time:
- Snow conditions at Squaw Valley via **Open-Meteo** (free, no API key)
- Headlines from Tahoe Daily Tribune, Reno, Sacramento RSS feeds

Maya uses this automatically when users ask about local topics (snow, weather,
mountain, news, what's happening, etc). It's also injected into every social
post so she sounds current and grounded.

---

## Social Media Automation

**Scheduler:** Run `python scheduler.py` separately from the web server.
Generates 4 posts/day (configurable) at random times between 8am–11pm.

**Post types (weighted):**
| Type | Weight | Image |
|---|---|---|
| General Maya voice | 40% | No |
| Squaw Valley / snowboarding | 25% | Yes |
| Bar shift | 20% | No |
| Selfie / candid | 15% | Yes |

**Flow:**
1. Scheduler generates post → status: `pending`
2. You review at `/admin/dashboard`
3. "Post to X now" → fires immediately
4. "Approve" → holds for auto-post (if `AUTO_POST=true`)
5. "Reject" → discarded

**Instagram:** Stubbed in `social_service.py`. Needs Meta Developer app approval.

---

## Image Generation — Current State & Roadmap

**Current:** ModelsLab SDXL — random photorealistic women. Works as a placeholder.

**Problem:** No character consistency. Every image is a different person.

**Solution needed:** LoRA fine-tuned on Maya's visual identity.

**Steps to fix:**
1. Define Maya's visual identity (reference photos or commission art)
2. Train or find a LoRA on Civitai.com
3. Switch to **Replicate.com** (pay-per-image, ~$0.01–0.05, supports LoRA)
4. Update `app/ai/image.py` with new provider + model ID
5. Add a standard prompt prefix: `maya, [description], photorealistic, natural lighting`

**To provide before this can be built:**
- LoRA model ID or Replicate model URL
- Maya's visual description (hair, features, style)

---

## Environment Variables — Complete List

```bash
# ModelsLab
MODELSLAB_API_KEY=
MODELSLAB_MODEL=ModelsLab/Llama-3.1-8b-Uncensored-Dare
MODELSLAB_API_URL=https://modelslab.com/api/uncensored-chat/v1/chat/completions
MODELSLAB_IMAGE_URL=https://modelslab.com/api/v6/images/text2img
MODELSLAB_IMAGE_MODEL=sdxl

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# CCBill (fill after approval)
CCBILL_ACCOUNT_NUM=
CCBILL_SUBACCOUNT=
CCBILL_SECRET_KEY=

# X (Twitter)
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# App
DATABASE_PATH=data/maya.db
PERSONA_FILE=persona/maya.txt
SECRET_KEY=change-me-in-production
DEV_MODE=true              # set false in production

# Admin
ADMIN_SECRET=              # your private admin password

# Social
POSTS_PER_DAY=4
AUTO_POST=false            # set true to auto-publish approved posts
```

---

## Setup Checklist — First Run

- [ ] Rename `.env.example` to `.env` and fill in values
- [ ] Create Supabase project → copy URL + anon key + service key
- [ ] Add ModelsLab API key (already in old project)
- [ ] Set `ADMIN_SECRET` to something private
- [ ] Run: `pip install -r requirements.txt`
- [ ] Run: `python -m uvicorn app.main:app --reload`
- [ ] Visit `localhost:8000` — landing page should load
- [ ] Register an account, verify age, send a message
- [ ] Visit `localhost:8000/admin` — enter admin secret

---

## Deployment Checklist — Railway

- [ ] Push to GitHub
- [ ] Connect repo to Railway
- [ ] Add all env vars in Railway dashboard (without DEV_MODE)
- [ ] Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Point `magicmaya.vip` DNS to Railway URL
- [ ] Add scheduler as a separate Railway service or cron job:
      `python scheduler.py`
- [ ] Apply for CCBill (needs live site URL)

---

## Open Items — Next Session

- [ ] Wire Replicate.com image generation (replace ModelsLab for images)
- [ ] LoRA / consistent character model for Maya's visual identity
- [ ] CCBill full webhook implementation (pending account approval)
- [ ] Instagram posting (pending Meta API access)
- [ ] Admin: manual credit adjustment UI (give/remove credits from users)
- [ ] Push notifications for mobile app
- [ ] Migrate SQLite → Supabase Postgres when ready to scale
- [ ] Delete legacy `templates/admin.html` (replaced by admin_dashboard.html)
