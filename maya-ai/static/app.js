// ── Auth helpers ──────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('maya_token')
}

function logout() {
  localStorage.removeItem('maya_token')
  localStorage.removeItem('maya_user_id')
  window.location.href = '/login'
}

if (!getToken()) {
  window.location.href = '/login'
}


// ── Credits ───────────────────────────────────────────────────────────────────

async function fetchCredits() {
  try {
    const res = await fetch('/api/payments/balance', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    if (res.status === 401) { logout(); return }
    const data = await res.json()
    updateCreditsDisplay(data.balance)
  } catch (err) {
    console.error('Could not fetch credits:', err)
  }
}

function updateCreditsDisplay(balance) {
  const valueEl = document.getElementById('credits-value')
  const badgeEl = document.getElementById('credits-display')
  if (!valueEl) return
  valueEl.textContent = balance
  badgeEl.classList.toggle('credits-badge--low', balance <= 5)
}


// ── Paywall ───────────────────────────────────────────────────────────────────

let selectedPackage = 'popular'

async function openPaywall() {
  document.getElementById('paywall-overlay').classList.remove('hidden')
  try {
    const res  = await fetch('/api/payments/packages')
    const pkgs = await res.json()
    renderPackages(pkgs)
  } catch (err) {
    console.error('Could not load packages:', err)
  }
}

function closePaywall() {
  document.getElementById('paywall-overlay').classList.add('hidden')
}

function renderPackages(pkgs) {
  const container = document.getElementById('credit-packs')
  const labels    = { starter: 'Starter', popular: 'Popular', premium: 'Premium' }
  const badges    = { popular: 'BEST VALUE' }

  container.innerHTML = Object.entries(pkgs).map(([key, pkg]) => `
    <div class="credit-pack ${key === selectedPackage ? 'selected' : ''}"
         onclick="selectPackage('${key}', this)">
      <div>
        <div class="credit-pack__label">${pkg.label || key}${pkg.badge ? ` <span class="credit-pack__badge">${pkg.badge}</span>` : ''}</div>
        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">${pkg.description || ''}</div>
      </div>
      <div style="text-align:right;flex-shrink:0;margin-left:12px;">
        <div style="font-family:var(--font-mono);color:var(--text-primary);font-size:1rem;">
          $${(pkg.amount_cents / 100).toFixed(2)}
        </div>
        <div style="font-size:0.72rem;color:var(--text-muted);">${pkg.credits} credits</div>
      </div>
    </div>
  `).join('')
}

function selectPackage(key, el) {
  selectedPackage = key
  document.querySelectorAll('.credit-pack').forEach(e => e.classList.remove('selected'))
  el.classList.add('selected')
}

async function purchaseSelected() {
  try {
    const res = await fetch('/api/payments/purchase', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({ package: selectedPackage })
    })
    const data = await res.json()
    if (res.status === 503) { alert(data.detail); return }
    if (data.payment_url) { window.location.href = data.payment_url }
  } catch (err) {
    console.error('Purchase error:', err)
  }
}


// ── Typing indicator ──────────────────────────────────────────────────────────

function showTyping() {
  const messages = document.getElementById('messages')
  const el = document.createElement('div')
  el.className = 'message message--maya'
  el.id = 'typing-indicator'
  el.innerHTML = `
    <div class="message__avatar message__avatar--initials"
         style="width:32px;height:32px;border-radius:999px;display:flex;align-items:center;
                justify-content:center;background:var(--bg-elevated);font-size:0.7rem;
                color:var(--text-accent);">M</div>
    <div class="typing-indicator"><span></span><span></span><span></span></div>
  `
  messages.appendChild(el)
  scrollToBottom()
}

function hideTyping() {
  const el = document.getElementById('typing-indicator')
  if (el) el.remove()
}


// ── Message rendering ─────────────────────────────────────────────────────────

function appendMessage(role, content) {
  const messages = document.getElementById('messages')
  const isMaya   = role === 'maya'
  const time     = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const wrapper  = document.createElement('div')
  wrapper.className = `message message--${isMaya ? 'maya' : 'user'}`

  let bubbleContent
  if (isMaya && content.startsWith('[IMAGE]') && content.includes('[/IMAGE]')) {
    const url = content.replace('[IMAGE]', '').replace('[/IMAGE]', '').trim()
    bubbleContent = `<div class="message__image"><img src="${url}" alt="Maya" loading="lazy"></div>`
  } else {
    bubbleContent = `<div class="message__bubble">${escapeHtml(content)}</div>`
  }

  if (isMaya) {
    wrapper.innerHTML = `
      <div class="message__avatar message__avatar--initials"
           style="width:32px;height:32px;border-radius:999px;display:flex;align-items:center;
                  justify-content:center;background:var(--bg-elevated);font-size:0.7rem;
                  color:var(--text-accent);">M</div>
      <div>${bubbleContent}<div class="message__time">${time}</div></div>
    `
  } else {
    wrapper.innerHTML = `
      <div>${bubbleContent}
      <div class="message__time" style="text-align:right;">${time}</div></div>
    `
  }

  messages.appendChild(wrapper)
  scrollToBottom()
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function scrollToBottom() {
  const body = document.getElementById('chat-body')
  if (body) body.scrollTop = body.scrollHeight
}


// ── Send ──────────────────────────────────────────────────────────────────────

async function send() {
  const input = document.getElementById('msg')
  const text  = input.value.trim()
  if (!text) return

  appendMessage('user', text)
  input.value = ''
  autoResize(input)
  showTyping()

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({ message: text })
    })

    hideTyping()

    if (res.status === 401) { logout(); return }

    // Age not verified — redirect to age gate
    if (res.status === 403) {
      window.location.href = '/age-verify'
      return
    }

    if (res.status === 429) {
      appendMessage('maya', 'slow down a little. too many messages at once.')
      return
    }

    if (res.status === 402) {
      appendMessage('maya', "you're out of credits. tap \"+ Get Credits\" to keep going.")
      openPaywall()
      return
    }

    const data = await res.json()
    appendMessage('maya', data.reply)

    if (data.followup) {
      showTyping()
      await delay(2000 + Math.random() * 2000)
      hideTyping()
      appendMessage('maya', data.followup)
    }

    fetchCredits()

  } catch (err) {
    hideTyping()
    appendMessage('maya', 'something went wrong on my end. try again.')
    console.error(err)
  }
}


// ── Input helpers ─────────────────────────────────────────────────────────────

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function autoResize(el) {
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}


// ── Init ──────────────────────────────────────────────────────────────────────

fetchCredits()
