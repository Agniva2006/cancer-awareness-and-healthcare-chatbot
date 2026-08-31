// ===== CONFIGURATION =====
const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? "http://localhost:8000"
    : (window.location.origin.includes('onrender.com') ? window.location.origin : "https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com");
const MAX_CHARS = 500;

// ===== DOM REFERENCES =====
const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const charCount = document.getElementById('char-count');
const suggestionsOverlay = document.getElementById('suggestions-overlay');
const sidebar = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const historyList = document.getElementById('history-list');
const historySearchInput = document.getElementById('history-search-input');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const exportBtn = document.getElementById('export-btn');
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const voiceInputBtn = document.getElementById('voice-input-btn');
const ttsToggleBtn = document.getElementById('tts-toggle-btn');
const voiceMicBtn = document.getElementById('voice-mic-btn');
const voiceRecordingBar = document.getElementById('voice-recording-bar');
const stopRecordingBtn = document.getElementById('stop-recording-btn');
const statusIndicator = document.getElementById('status-indicator');
const toastContainer = document.getElementById('toast-container');
const particlesCanvas = document.getElementById('particles-canvas');
const imageUploadBtn = document.getElementById('image-upload-btn');
const imageFileInput = document.getElementById('image-file-input');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreviewImg = document.getElementById('image-preview-img');
const imagePreviewRemove = document.getElementById('image-preview-remove');
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxClose = document.getElementById('lightbox-close');
const inputContainer = document.getElementById('input-container');

// ===== STATE =====
let currentSessionId = null;
let sessions = {};
let ttsEnabled = false;
let isRecording = false;
let recognition = null;
let queryCount = 0;
let totalConfidence = 0;
let totalLatency = 0;
let userMessageCount = 0;
let pendingImageDataUrl = null;
let currentMode = 'clinical';
let activePanel = 'chat-panel';

// ===== AUTH STATE =====
let currentUser = null;    // { username, email, full_name, specialty, plan, ... }
let authToken = null;      // JWT string

// Plan hierarchy for gating
const PLAN_LEVELS = { free: 0, clinical: 1, enterprise: 2 };

// ===== INIT =====
function init() {
    loadSessions();
    loadTheme();
    setupAuth();
    startNewSession();
    setupParticles();
    setupTextareaAutoResize();
    setupNavTabs();
    setupGraphPanel();
    setupTumorBoardPanel();
    setupFederatedPanel();
    setupMLPanel();
    updateStats();
    loadGraphStats();
    setupPasswordStrengthMeter();
}

// ══════════════════════════════════════════════════════
// AUTH SYSTEM — JWT-based
// ══════════════════════════════════════════════════════

function getAuthHeaders() {
    if (!authToken) return { 'Content-Type': 'application/json' };
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    };
}

function decodeJwt(token) {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch { return null; }
}

function isTokenExpired(token) {
    const payload = decodeJwt(token);
    if (!payload || !payload.exp) return true;
    return Date.now() / 1000 > payload.exp;
}

function scheduleTokenExpiryCheck() {
    const payload = decodeJwt(authToken);
    if (!payload || !payload.exp) return;
    const msUntilExpiry = (payload.exp * 1000) - Date.now();
    if (msUntilExpiry > 0) {
        // Warn 5 min before expiry
        const warnMs = msUntilExpiry - 5 * 60 * 1000;
        if (warnMs > 0) {
            setTimeout(() => {
                showNotifBanner('Your session expires in 5 minutes. <span class="nb-link" onclick="document.getElementById(\'logout-btn\').click()">Re-login</span>', 'warning');
            }, warnMs);
        }
        setTimeout(() => {
            showToast('Session expired. Please login again.', 'error');
            doLogout();
        }, msUntilExpiry);
    }
}

function setupAuth() {
    const authOverlay = document.getElementById('auth-overlay');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const forgotForm = document.getElementById('forgot-form');
    const logoutBtn = document.getElementById('logout-btn');
    const userChipBtn = document.getElementById('user-chip-btn');

    // ── Check persisted session ──
    const savedToken = localStorage.getItem('onco_token');
    const savedUser = localStorage.getItem('onco_user');

    if (savedToken && savedUser && !isTokenExpired(savedToken)) {
        authToken = savedToken;
        currentUser = JSON.parse(savedUser);
        authOverlay.classList.remove('active');
        onLoginSuccess(currentUser, false);
    } else {
        localStorage.removeItem('onco_token');
        localStorage.removeItem('onco_user');
        authOverlay.classList.add('active');
    }

    // ── Login form submit ──
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        const rememberMe = document.getElementById('remember-me').checked;

        setAuthMsg('', '');
        setAuthBtnLoading('login-btn', true, 'Authorizing...');

        try {
            const resp = await fetch(API_URL + '/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, remember_me: rememberMe })
            });
            const data = await resp.json();
            if (data.success) {
                authToken = data.access_token;
                currentUser = data.user;
                localStorage.setItem('onco_token', authToken);
                localStorage.setItem('onco_user', JSON.stringify(currentUser));
                authOverlay.classList.remove('active');
                onLoginSuccess(currentUser, !currentUser.onboarding_done);
            } else {
                setAuthMsg(data.message || 'Login failed.', 'error');
            }
        } catch {
            setAuthMsg('Cannot reach the server. Please check backend is running.', 'error');
        } finally {
            setAuthBtnLoading('login-btn', false, '&#x1F511; Authorize Access');
        }
    });

    // ── Register form submit ──
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('reg-username').value.trim();
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value;
        const fullName = document.getElementById('reg-fullname').value.trim();
        const specialty = document.getElementById('reg-specialty').value;
        const institution = document.getElementById('reg-institution').value.trim();
        const role = document.getElementById('reg-role').value;

        setAuthMsg('', '');
        setAuthBtnLoading('register-btn', true, 'Creating account...');

        try {
            const resp = await fetch(API_URL + '/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password, full_name: fullName, specialty, institution, role })
            });
            const data = await resp.json();
            if (data.success) {
                setAuthMsg(data.message + ' Please sign in.', 'success');
                setTimeout(() => switchAuthTab('login'), 1500);
            } else {
                setAuthMsg(data.message || 'Registration failed.', 'error');
            }
        } catch {
            setAuthMsg('Cannot reach the server.', 'error');
        } finally {
            setAuthBtnLoading('register-btn', false, '&#x1F195; Create Clinical Account');
        }
    });

    // ── Forgot password ──
    forgotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('forgot-username').value.trim();
        if (!username) return;
        // Generate a fake reset token (UI only)
        const fakeToken = btoa(username + ':' + Date.now()).replace(/=/g, '').substring(0, 32);
        document.getElementById('reset-token-value').textContent = fakeToken;
        document.getElementById('reset-token-box').style.display = 'block';
    });

    // ── Logout ──
    logoutBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to log out?')) doLogout();
    });

    // ── User chip opens profile ──
    if (userChipBtn) {
        userChipBtn.addEventListener('click', openProfileModal);
    }
}

function onLoginSuccess(user, showOnboarding = false) {
    scheduleTokenExpiryCheck();
    renderUserChip(user);
    updatePlanGates(user.plan || 'free');
    refreshUsageBar();
    loadGraphStats();
    showToast(`Welcome${user.full_name ? ', ' + user.full_name.split(' ')[0] : ''}! You're on the ${capitalise(user.plan || 'free')} plan.`, 'success');

    if (showOnboarding) {
        setTimeout(() => openOnboarding(), 400);
    }
}

function doLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('onco_token');
    localStorage.removeItem('onco_user');
    document.getElementById('auth-overlay').classList.add('active');
    document.getElementById('login-form').reset();
    document.getElementById('register-form').reset();
    document.getElementById('user-chip-btn').style.display = 'none';
    document.getElementById('sidebar-usage-bar').style.display = 'none';
    document.getElementById('upgrade-nudge').style.display = 'none';
    updatePlanGates('free');
    showToast('Logged out successfully', 'info');
}

function setAuthMsg(msg, type) {
    const el = document.getElementById('auth-msg');
    el.textContent = msg;
    el.className = 'auth-msg' + (msg && type ? ' ' + type : '');
}

function setAuthBtnLoading(id, loading, html) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading ? '⏳ ' + html : html;
}

// Auth tab switcher
window.switchAuthTab = function(tab) {
    ['login', 'register', 'forgot'].forEach(t => {
        document.getElementById('auth-tab-' + t)?.classList.toggle('active', t === tab);
        document.getElementById('auth-pane-' + t)?.classList.toggle('active', t === tab);
    });
    setAuthMsg('', '');
};

// ══════════════════════════════════════════════════════
// PLAN GATES — show/hide lock overlays & badges
// ══════════════════════════════════════════════════════

function updatePlanGates(plan) {
    const lvl = PLAN_LEVELS[plan] ?? 0;

    // Graph: clinical+
    const graphLocked = lvl < PLAN_LEVELS.clinical;
    setOverlay('lock-overlay-graph', graphLocked);
    setLockPip('lock-graph', graphLocked);

    // ML: clinical+
    const mlLocked = lvl < PLAN_LEVELS.clinical;
    setOverlay('lock-overlay-ml', mlLocked);
    setLockPip('lock-ml', mlLocked);

    // Tumor board & Federated: enterprise only
    const entLocked = lvl < PLAN_LEVELS.enterprise;
    setOverlay('lock-overlay-tumor', entLocked);
    setLockPip('lock-tumor', entLocked);
    setOverlay('lock-overlay-federated', entLocked);
    setLockPip('lock-federated', entLocked);

    // Show upgrade nudge for free users
    const nudge = document.getElementById('upgrade-nudge');
    if (nudge) nudge.style.display = plan === 'free' ? 'block' : 'none';
}

function setOverlay(id, show) {
    const el = document.getElementById(id);
    if (el) el.style.display = show ? 'flex' : 'none';
}

function setLockPip(id, show) {
    const el = document.getElementById(id);
    if (el) el.style.display = show ? 'inline' : 'none';
}

function checkPlanGate(requiredPlan) {
    if (!currentUser) return false;
    const userLevel = PLAN_LEVELS[currentUser.plan || 'free'] ?? 0;
    const reqLevel = PLAN_LEVELS[requiredPlan] ?? 0;
    if (userLevel >= reqLevel) return true;
    openSubscriptionModal();
    return false;
}

// ══════════════════════════════════════════════════════
// USER CHIP & SIDEBAR UI
// ══════════════════════════════════════════════════════

function renderUserChip(user) {
    const chip = document.getElementById('user-chip-btn');
    if (!chip) return;

    const initials = getInitials(user.full_name || user.username);
    const color = user.avatar_color || '#6366f1';
    const plan = user.plan || 'free';

    document.getElementById('sidebar-avatar').textContent = initials;
    document.getElementById('sidebar-avatar').style.background = color;
    document.getElementById('sidebar-username').textContent = user.full_name || user.username;

    const planBadge = document.getElementById('sidebar-plan-badge');
    planBadge.textContent = capitalise(plan);
    planBadge.className = 'plan-badge ' + plan;

    chip.style.display = 'flex';
    document.getElementById('sidebar-usage-bar').style.display = 'block';
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function capitalise(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

async function refreshUsageBar() {
    if (!authToken || !currentUser) return;
    try {
        const resp = await fetch(API_URL + '/auth/usage', { headers: getAuthHeaders() });
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        const u = data.usage;

        // Sidebar usage bar
        const pct = u.daily_quota === 999999 ? 0 : Math.min(100, (u.queries_today / u.daily_quota) * 100);
        const fill = document.getElementById('uqb-fill');
        const countEl = document.getElementById('uqb-count');
        if (fill) {
            fill.style.width = pct + '%';
            fill.className = 'uqb-fill' + (pct >= 80 ? ' danger' : '');
        }
        if (countEl) {
            countEl.textContent = u.daily_quota === 999999 ? `${u.queries_today} used` : `${u.queries_today}/${u.daily_quota}`;
        }
    } catch {}
}

// ══════════════════════════════════════════════════════
// PROFILE MODAL
// ══════════════════════════════════════════════════════

window.openProfileModal = function() {
    if (!currentUser) return;
    const modal = document.getElementById('profile-modal');
    modal.classList.add('active');
    loadProfileData();
    switchProfileTab('info');
};

window.closeProfileModal = function() {
    document.getElementById('profile-modal').classList.remove('active');
};

window.switchProfileTab = function(tab) {
    document.querySelectorAll('.profile-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-ptab') === tab));
    document.querySelectorAll('.profile-pane').forEach(p => p.classList.toggle('active', p.id === 'ptab-' + tab));

    if (tab === 'usage') loadUsageTab();
    if (tab === 'activity') loadActivityTab();
    if (tab === 'sessions') loadSessionsTab();
};

function loadProfileData() {
    if (!currentUser) return;
    document.getElementById('pf-fullname').value = currentUser.full_name || '';
    document.getElementById('pf-username').value = currentUser.username || '';
    document.getElementById('pf-email').value = currentUser.email || '';
    document.getElementById('pf-specialty').value = currentUser.specialty || '';
    document.getElementById('pf-institution').value = currentUser.institution || '';

    // Header
    const initials = getInitials(currentUser.full_name || currentUser.username);
    const color = currentUser.avatar_color || '#6366f1';
    const avatar = document.getElementById('profile-avatar-large');
    avatar.textContent = initials;
    avatar.style.background = color;

    document.getElementById('profile-header-name').textContent = currentUser.full_name || currentUser.username;
    document.getElementById('profile-role-tag').textContent = capitalise(currentUser.role || 'clinician');

    const pb = document.getElementById('profile-plan-badge');
    pb.textContent = capitalise(currentUser.plan || 'free');
    pb.className = 'plan-badge ' + (currentUser.plan || 'free');

    const since = currentUser.created_at ? new Date(currentUser.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) : '—';
    document.getElementById('profile-since').textContent = 'Since ' + since;
}

window.saveProfileInfo = async function() {
    if (!authToken) return;
    const btn = document.getElementById('pf-save-info-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    const body = {
        full_name: document.getElementById('pf-fullname').value.trim(),
        email: document.getElementById('pf-email').value.trim(),
        specialty: document.getElementById('pf-specialty').value.trim(),
        institution: document.getElementById('pf-institution').value.trim(),
    };

    try {
        const resp = await fetch(API_URL + '/auth/profile/update', {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        const data = await resp.json();
        if (data.success) {
            currentUser = { ...currentUser, ...data.user };
            localStorage.setItem('onco_user', JSON.stringify(currentUser));
            renderUserChip(currentUser);
            loadProfileData();
            showPfMsg('pf-info-msg', 'Profile updated successfully!', 'success');
        } else {
            showPfMsg('pf-info-msg', data.detail || 'Update failed.', 'error');
        }
    } catch {
        showPfMsg('pf-info-msg', 'Server error. Try again.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Changes';
    }
};

window.changePassword = async function() {
    if (!authToken) return;
    const oldPw = document.getElementById('pf-old-pw').value;
    const newPw = document.getElementById('pf-new-pw').value;
    const confirmPw = document.getElementById('pf-confirm-pw').value;

    if (newPw !== confirmPw) { showPfMsg('pf-security-msg', 'New passwords do not match.', 'error'); return; }
    if (newPw.length < 6) { showPfMsg('pf-security-msg', 'New password must be at least 6 characters.', 'error'); return; }

    try {
        const resp = await fetch(API_URL + '/auth/profile/change-password', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ old_password: oldPw, new_password: newPw })
        });
        const data = await resp.json();
        if (data.success) {
            showPfMsg('pf-security-msg', 'Password changed successfully!', 'success');
            document.getElementById('pf-old-pw').value = '';
            document.getElementById('pf-new-pw').value = '';
            document.getElementById('pf-confirm-pw').value = '';
        } else {
            showPfMsg('pf-security-msg', data.detail || 'Password change failed.', 'error');
        }
    } catch {
        showPfMsg('pf-security-msg', 'Server error. Try again.', 'error');
    }
};

async function loadUsageTab() {
    if (!authToken) return;
    try {
        const resp = await fetch(API_URL + '/auth/usage', { headers: getAuthHeaders() });
        const data = await resp.json();
        if (!data.success) return;
        const u = data.usage;

        document.getElementById('pf-queries-today').textContent = u.queries_today;
        document.getElementById('pf-queries-month').textContent = u.queries_month;
        document.getElementById('pf-daily-remaining').textContent = u.daily_quota === 999999 ? '∞' : u.daily_remaining;
        document.getElementById('pf-monthly-remaining').textContent = u.monthly_quota === 999999 ? '∞' : u.monthly_remaining;

        const dailyPct = u.daily_quota === 999999 ? 5 : Math.min(100, (u.queries_today / u.daily_quota) * 100);
        const monthlyPct = u.monthly_quota === 999999 ? 5 : Math.min(100, (u.queries_month / u.monthly_quota) * 100);

        const dailyBar = document.getElementById('pf-daily-bar');
        dailyBar.style.width = dailyPct + '%';
        dailyBar.className = 'uqb-fill-lg' + (dailyPct >= 80 ? ' danger' : '');

        const monthlyBar = document.getElementById('pf-monthly-bar');
        monthlyBar.style.width = monthlyPct + '%';
        monthlyBar.className = 'uqb-fill-lg' + (monthlyPct >= 80 ? ' danger' : '');

        document.getElementById('pf-daily-label').textContent = u.daily_quota === 999999 ? `${u.queries_today} / ∞` : `${u.queries_today} / ${u.daily_quota}`;
        document.getElementById('pf-monthly-label').textContent = u.monthly_quota === 999999 ? `${u.queries_month} / ∞` : `${u.queries_month} / ${u.monthly_quota}`;
    } catch {}
}

async function loadActivityTab() {
    if (!authToken) return;
    const container = document.getElementById('pf-activity-content');
    try {
        const resp = await fetch(API_URL + '/auth/activity', { headers: getAuthHeaders() });
        const data = await resp.json();
        if (!data.success || data.activity.length === 0) {
            container.innerHTML = '<div class="activity-empty">No activity recorded yet.</div>';
            return;
        }
        container.innerHTML = `
            <table class="activity-table">
                <thead><tr><th>#</th><th>Endpoint</th><th>Time</th></tr></thead>
                <tbody>
                    ${data.activity.map((a, i) => `
                        <tr>
                            <td>${i + 1}</td>
                            <td><code>${escapeHtml(a.endpoint)}</code></td>
                            <td>${new Date(a.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch {
        container.innerHTML = '<div class="activity-empty">Failed to load activity.</div>';
    }
}

async function loadSessionsTab() {
    if (!authToken) return;
    const container = document.getElementById('pf-sessions-content');
    try {
        const resp = await fetch(API_URL + '/auth/sessions', { headers: getAuthHeaders() });
        const data = await resp.json();
        if (!data.success || data.sessions.length === 0) {
            container.innerHTML = '<div class="activity-empty">No sessions recorded.</div>';
            return;
        }
        container.innerHTML = data.sessions.map((s, i) => `
            <div class="session-item">
                <div class="session-dot"></div>
                <span>Login ${i === 0 ? '(Most Recent)' : ''}</span>
                <span>${new Date(s.login_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        `).join('');
    } catch {
        container.innerHTML = '<div class="activity-empty">Failed to load sessions.</div>';
    }
}

window.logoutAllSessions = function() {
    if (confirm('This will log you out of all devices. Proceed?')) {
        doLogout();
    }
};

function showPfMsg(id, msg, type) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.className = 'pf-msg ' + type;
    setTimeout(() => { el.className = 'pf-msg'; el.textContent = ''; }, 4000);
}

// ══════════════════════════════════════════════════════
// SUBSCRIPTION MODAL
// ══════════════════════════════════════════════════════

window.openSubscriptionModal = function() {
    const modal = document.getElementById('subscription-modal');
    modal.classList.add('active');
    renderPricingCards();
};

window.closeSubscriptionModal = function() {
    document.getElementById('subscription-modal').classList.remove('active');
};

function renderPricingCards() {
    const grid = document.getElementById('plans-grid');
    const userPlan = currentUser?.plan || 'free';

    const plans = [
        {
            id: 'free',
            name: 'Free',
            price: '$0',
            period: '/month',
            desc: 'Basic cancer Q&A for patients and caregivers',
            highlights: ['10 AI queries per day', 'Basic cancer chatbot', 'Chat history & export', 'Voice input & TTS'],
            popular: false,
        },
        {
            id: 'clinical',
            name: 'Clinical',
            price: '$49',
            period: '/month',
            desc: 'For oncologists & clinical teams',
            highlights: ['500 AI queries per day', 'Knowledge Graph Explorer', 'ML Prognosis Predictor', 'DICOM image analysis', 'Clinical mode & ICD-10 codes'],
            popular: true,
        },
        {
            id: 'enterprise',
            name: 'Enterprise',
            price: '$199',
            period: '/month',
            desc: 'Full platform for hospital networks',
            highlights: ['Unlimited queries', 'Virtual Tumor Board (4 AI agents)', 'Federated Learning Network', 'All Clinical features', 'Priority support & SLA'],
            popular: false,
        },
    ];

    grid.innerHTML = plans.map(p => {
        const isCurrent = p.id === userPlan;
        const isDowngrade = PLAN_LEVELS[p.id] < PLAN_LEVELS[userPlan];
        let btnClass = 'plan-cta-btn ';
        let btnText = '';
        if (isCurrent) { btnClass += 'current-plan'; btnText = '✓ Current Plan'; }
        else if (isDowngrade) { btnClass += 'outline'; btnText = 'Switch to ' + p.name; }
        else { btnClass += 'primary'; btnText = '⚡ Upgrade to ' + p.name; }

        return `
            <div class="plan-card${isCurrent ? ' current' : ''}${p.popular && !isCurrent ? ' popular' : ''}">
                ${p.popular && !isCurrent ? '<div class="popular-badge">Most Popular</div>' : ''}
                ${isCurrent ? '<div class="current-badge">✓ Active</div>' : ''}
                <div class="plan-name">${p.name}</div>
                <div class="plan-price">${p.price}<span>${p.period}</span></div>
                <div class="plan-desc">${p.desc}</div>
                <ul class="plan-features">
                    ${p.highlights.map(h => `<li>${h}</li>`).join('')}
                </ul>
                <button class="${btnClass}" onclick="selectPlan('${p.id}')" ${isCurrent ? 'disabled' : ''}>${btnText}</button>
            </div>`;
    }).join('');
}

window.selectPlan = async function(planId) {
    if (!authToken || !currentUser) { showToast('Please login to change plan.', 'error'); return; }
    if (planId === currentUser.plan) return;

    try {
        const resp = await fetch(API_URL + '/auth/upgrade-plan', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ plan: planId })
        });
        const data = await resp.json();
        if (data.success) {
            currentUser.plan = planId;
            localStorage.setItem('onco_user', JSON.stringify(currentUser));
            renderUserChip(currentUser);
            updatePlanGates(planId);
            renderPricingCards();
            showToast(`Plan changed to ${capitalise(planId)}! New features are now unlocked.`, 'success');
            // Close after short delay
            setTimeout(() => closeSubscriptionModal(), 1200);
        } else {
            showToast(data.detail || 'Plan change failed.', 'error');
        }
    } catch {
        showToast('Server error. Try again.', 'error');
    }
};

// ══════════════════════════════════════════════════════
// ONBOARDING WIZARD
// ══════════════════════════════════════════════════════

let obStep = 0;
let obRole = '';
let obFocus = '';
let obQuery = '';

function openOnboarding() {
    document.getElementById('onboarding-overlay').classList.add('active');
    obStep = 0;
    renderObStep();
}

function closeOnboarding() {
    document.getElementById('onboarding-overlay').classList.remove('active');
}

function renderObStep() {
    [0, 1, 2].forEach(i => {
        document.getElementById('ob-step-' + i).classList.toggle('active', i === obStep);
        const dot = document.getElementById('ob-dot-' + i);
        dot.classList.toggle('active', i === obStep);
        dot.classList.toggle('done', i < obStep);
    });
}

window.selectObOption = function(el, type) {
    el.closest('.ob-options-grid').querySelectorAll('.ob-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    if (type === 'role') obRole = el.getAttribute('data-ob-role');
    if (type === 'focus') obFocus = el.getAttribute('data-ob-focus');
};

window.selectObChip = function(el) {
    el.closest('.ob-sample-chips').querySelectorAll('.ob-chip').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    obQuery = el.getAttribute('data-query');
};

window.obNext = function() {
    if (obStep < 2) { obStep++; renderObStep(); }
};

window.obBack = function() {
    if (obStep > 0) { obStep--; renderObStep(); }
};

window.finishOnboarding = async function() {
    closeOnboarding();
    // Mark onboarding done
    if (authToken) {
        try {
            await fetch(API_URL + '/auth/onboarding-complete', {
                method: 'POST',
                headers: getAuthHeaders()
            });
        } catch {}
    }
    if (currentUser) currentUser.onboarding_done = true;

    // Auto-fire selected query
    if (obQuery) {
        switchPanel('chat-panel');
        setTimeout(() => {
            userInput.value = obQuery;
            chatForm.dispatchEvent(new Event('submit'));
        }, 300);
    }
};

// ══════════════════════════════════════════════════════
// PASSWORD STRENGTH METER
// ══════════════════════════════════════════════════════

function setupPasswordStrengthMeter() {
    const pwInput = document.getElementById('reg-password');
    if (pwInput) {
        pwInput.addEventListener('input', () => {
            updatePwStrength(pwInput.value, 'strength-fill', 'strength-label');
        });
    }
}

window.updatePwStrength = function(pw, fillId, labelId) {
    const fill = document.getElementById(fillId);
    const label = document.getElementById(labelId);
    if (!fill || !label) return;

    let score = 0;
    if (pw.length >= 6) score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    const levels = [
        { cls: '', pct: '0%', text: 'Enter password' },
        { cls: 'weak', pct: '25%', text: 'Weak' },
        { cls: 'fair', pct: '50%', text: 'Fair' },
        { cls: 'good', pct: '75%', text: 'Good' },
        { cls: 'strong', pct: '100%', text: 'Strong' },
    ];
    const lvl = pw.length === 0 ? 0 : Math.min(4, score);
    fill.className = 'strength-bar-fill ' + levels[lvl].cls;
    fill.style.width = levels[lvl].pct;
    label.className = 'strength-label ' + levels[lvl].cls;
    label.textContent = levels[lvl].text;
};

// ══════════════════════════════════════════════════════
// NOTIFICATION BANNER
// ══════════════════════════════════════════════════════

function showNotifBanner(htmlMsg, type = 'info') {
    const area = document.getElementById('notif-banner-area');
    if (!area) return;
    const div = document.createElement('div');
    div.className = `notif-banner ${type}`;
    div.innerHTML = htmlMsg;
    area.appendChild(div);
    setTimeout(() => div.remove(), 10000);
}

// ══════════════════════════════════════════════════════
// NAVIGATION TABS (with plan gating)
// ══════════════════════════════════════════════════════

function setupNavTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const panelId = tab.getAttribute('data-panel');
            const planRequired = tab.getAttribute('data-plan-required');

            if (planRequired && currentUser) {
                const userLevel = PLAN_LEVELS[currentUser.plan || 'free'] ?? 0;
                const reqLevel = PLAN_LEVELS[planRequired] ?? 0;
                if (userLevel < reqLevel) {
                    // Still switch panel but show lock overlay (already shown by updatePlanGates)
                    switchPanel(panelId);
                    return;
                }
            }
            switchPanel(panelId);
        });
    });
}

function switchPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

    const panel = document.getElementById(panelId);
    if (panel) panel.classList.add('active');

    const tab = document.querySelector(`[data-panel="${panelId}"]`);
    if (tab) tab.classList.add('active');

    activePanel = panelId;

    if (inputContainer) {
        inputContainer.style.display = panelId === 'chat-panel' ? '' : 'none';
    }
}

// ===== PARTICLES BACKGROUND =====
function setupParticles() {
    const canvas = particlesCanvas;
    const ctx = canvas.getContext('2d');
    let particles = [];
    const count = 50;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * 2 + 0.5,
            dx: (Math.random() - 0.5) * 0.4,
            dy: (Math.random() - 0.5) * 0.4,
            opacity: Math.random() * 0.5 + 0.1
        });
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
        const color = isDark ? '129,140,248' : '99,102,241';

        particles.forEach((p, i) => {
            p.x += p.dx;
            p.y += p.dy;
            if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.dy *= -1;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${color},${p.opacity})`;
            ctx.fill();

            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(${color},${0.06 * (1 - dist / 150)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        });
        requestAnimationFrame(draw);
    }
    draw();
}

// ===== TEXTAREA AUTO-RESIZE =====
function setupTextareaAutoResize() {
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        const len = userInput.value.length;
        charCount.textContent = `${len} / ${MAX_CHARS}`;
        if (len > MAX_CHARS) {
            userInput.value = userInput.value.substring(0, MAX_CHARS);
            charCount.textContent = `${MAX_CHARS} / ${MAX_CHARS}`;
        }
    });
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
}

// ===== SESSION MANAGEMENT =====
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 6);
}

function loadSessions() {
    try {
        const raw = localStorage.getItem('cancerAI_sessions');
        sessions = raw ? JSON.parse(raw) : {};
    } catch { sessions = {}; }
}

function saveSessions() {
    localStorage.setItem('cancerAI_sessions', JSON.stringify(sessions));
}

function startNewSession() {
    currentSessionId = generateId();
    sessions[currentSessionId] = {
        id: currentSessionId,
        title: 'New Conversation',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
    };
    saveSessions();
    renderHistory();
    clearChatWindow();
    userMessageCount = 0;
    suggestionsOverlay.classList.remove('hidden');
    showToast('New conversation started', 'info');
}

function clearChatWindow() {
    chatWindow.innerHTML = '';
    appendSystemWelcome();
}

function appendSystemWelcome() {
    const div = document.createElement('div');
    div.className = 'message system fade-in';
    div.innerHTML = `
        <div class="avatar bot-avatar">&#x1F9EC;</div>
        <div class="message-bubble">
            <div class="message-text">
                <p>Hello! I'm <strong>OncoGraph AI</strong> &mdash; your enterprise clinical intelligence copilot. I integrate knowledge graph reasoning, multi-agent tumor board analysis, and federated learning across 3 hospital networks.</p>
                <p>Choose a topic below or type your clinical question.</p>
            </div>
            <span class="disclaimer-badge">&#x2139;&#xFE0F; For clinical decision support only. Always consult a treating oncologist.</span>
        </div>
    `;
    chatWindow.appendChild(div);
}

function loadSession(sessionId) {
    if (!sessions[sessionId]) return;
    currentSessionId = sessionId;
    clearChatWindow();
    userMessageCount = 0;
    const session = sessions[sessionId];
    session.messages.forEach(msg => {
        if (msg.role === 'user') {
            userMessageCount++;
            appendMessage('user', `<p>${escapeHtml(msg.text)}</p>`, false);
        } else {
            appendMessage('system', msg.html, false);
        }
    });
    if (userMessageCount > 0) suggestionsOverlay.classList.add('hidden');
    else suggestionsOverlay.classList.remove('hidden');
    renderHistory();
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function deleteSession(sessionId) {
    delete sessions[sessionId];
    saveSessions();
    if (sessionId === currentSessionId) startNewSession();
    else renderHistory();
}

// ===== RENDER HISTORY =====
function renderHistory(filter = '') {
    historyList.innerHTML = '';
    const sorted = Object.values(sessions).sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    const filtered = filter ? sorted.filter(s => s.title.toLowerCase().includes(filter.toLowerCase())) : sorted;

    if (filtered.length === 0) {
        historyList.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:.8rem;padding:20px">No conversations yet</div>';
        return;
    }

    filtered.forEach(s => {
        const div = document.createElement('div');
        div.className = `history-item${s.id === currentSessionId ? ' active' : ''}`;
        const date = new Date(s.updatedAt);
        const timeStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const msgCount = s.messages.filter(m => m.role === 'user').length;
        div.innerHTML = `
            <span class="history-item-title">${escapeHtml(s.title)}</span>
            <span class="history-item-meta"><span>${timeStr}</span><span>${msgCount} msg${msgCount !== 1 ? 's' : ''}</span></span>
        `;
        div.addEventListener('click', () => loadSession(s.id));
        historyList.appendChild(div);
    });
    updateStats();
}

// ===== MESSAGES =====
function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function appendMessage(role, contentHTML, save = true) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    const avatar = role === 'user' ? '&#x1F464;' : '&#x1F9EC;';
    const avatarClass = role === 'user' ? '' : 'bot-avatar';

    msgDiv.innerHTML = `
        <div class="avatar ${avatarClass}">${avatar}</div>
        <div class="message-bubble">
            ${contentHTML}
        </div>
    `;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    if (save && sessions[currentSessionId]) {
        sessions[currentSessionId].messages.push({
            role,
            text: role === 'user' ? contentHTML.replace(/<[^>]*>/g, '') : '',
            html: contentHTML,
            timestamp: new Date().toISOString()
        });
        sessions[currentSessionId].updatedAt = new Date().toISOString();
        saveSessions();
    }
}

function showTyping() {
    const div = document.createElement('div');
    div.className = 'message system';
    div.id = 'typing-msg';
    div.innerHTML = `
        <div class="avatar bot-avatar">&#x1F9EC;</div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTyping() {
    const el = document.getElementById('typing-msg');
    if (el) el.remove();
}

function formatBotResponse(data) {
    let html = '';

    if (data.triage && (data.triage.level === 'RED' || data.triage.level === 'YELLOW')) {
        const isRed = data.triage.level === 'RED';
        html += `
            <div class="triage-alert-banner ${isRed ? 'red' : 'yellow'}">
                <div class="triage-alert-title">${isRed ? '&#x1F6A8; EMERGENCY TRIAGE ALERT' : '&#x26A0;&#xFE0F; CLINICAL ATTENTION RECOMMENDED'}</div>
                <div class="triage-alert-action">${escapeHtml(data.triage.action || '')}</div>
            </div>`;
    }

    let answerHtml = data.answer
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\* /g, '\n<li>')
        .replace(/\n- /g, '\n<li>');

    if (answerHtml.includes('<li>')) {
        answerHtml = answerHtml.replace(/((<li>.*?(?:\n|$))+)/g, '<ul>$1</ul>');
    }
    answerHtml = answerHtml.replace(/\n/g, '<br>');

    html += `<div class="message-text"><p>${answerHtml}</p></div>`;

    if (data.icd10 && data.icd10.length > 0) {
        html += `<div style="margin-top:8px"><strong>ICD-10 Codes:</strong> ${data.icd10.map(code => `<span class="icd10-badge">${escapeHtml(code)}</span>`).join('')}</div>`;
    }

    if (data.sources && data.sources.length > 0) {
        html += `<div class="sources-container"><div class="sources-title">Sources Consulted</div><div>${data.sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}</div></div>`;
    }

    if (data.confidence > 0 || data.latency > 0) {
        html += `<div class="metrics">`;
        if (data.confidence > 0) html += `<span class="metric-item">&#x1F3AF; ${(data.confidence * 100).toFixed(1)}%</span>`;
        if (data.latency > 0) html += `<span class="metric-item">&#x23F1;&#xFE0F; ${data.latency.toFixed(2)}s</span>`;
        if (data.mode) html += `<span class="metric-item">&#x1FA7A; Mode: ${escapeHtml(data.mode)}</span>`;
        if (data.rate_limit?.remaining !== undefined) html += `<span class="metric-item">&#x1F4CB; ${data.rate_limit.remaining} remaining</span>`;
        html += `</div>`;
    }

    if (data.disclaimer) {
        html += `<span class="disclaimer-badge">&#x26A0;&#xFE0F; ${escapeHtml(data.disclaimer)}</span>`;
    }

    html += `<button class="msg-tts-btn" onclick="speakText(this)" data-text="${escapeHtml(data.answer)}">&#x1F50A; Read Aloud</button>`;

    return html;
}

// ===== FORM SUBMIT =====
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    // Require auth
    if (!authToken) {
        showToast('Please log in to send queries.', 'error');
        document.getElementById('auth-overlay').classList.add('active');
        return;
    }

    userMessageCount++;
    if (userMessageCount >= 1) suggestionsOverlay.classList.add('hidden');

    let imagePayload = null;
    let userHtml = `<p>${escapeHtml(query)}</p>`;
    if (pendingImageDataUrl) {
        imagePayload = pendingImageDataUrl;
        userHtml += `<div class="user-attached-image" onclick="openLightbox('${pendingImageDataUrl}')"><img src="${pendingImageDataUrl}" alt="Attached image"></div>`;
        pendingImageDataUrl = null;
        imagePreviewContainer.classList.remove('active');
    }
    appendMessage('user', userHtml);

    if (sessions[currentSessionId] && sessions[currentSessionId].title === 'New Conversation') {
        sessions[currentSessionId].title = query.length > 40 ? query.substring(0, 40) + '...' : query;
        saveSessions();
        renderHistory();
    }

    userInput.value = '';
    userInput.style.height = 'auto';
    charCount.textContent = `0 / ${MAX_CHARS}`;
    sendBtn.disabled = true;
    showTyping();

    try {
        const history = (sessions[currentSessionId]?.messages || [])
            .slice(-6)
            .map(m => ({
                role: m.role === 'user' ? 'user' : 'assistant',
                content: m.role === 'user' ? m.text : (m.html ? m.html.replace(/<[^>]*>/g, '').slice(0, 300) : '')
            }));

        const resp = await fetch(API_URL + '/ask', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ query, chat_history: history, image_data: imagePayload, mode: currentMode })
        });
        removeTyping();

        if (resp.status === 401) {
            showToast('Session expired. Please log in again.', 'error');
            doLogout();
            return;
        }
        if (resp.status === 429) {
            const errData = await resp.json();
            showToast(errData.detail || 'Daily quota reached. Upgrade your plan!', 'error');
            showNotifBanner(`Daily query limit reached. <span class="nb-link" onclick="openSubscriptionModal()">Upgrade your plan</span> to continue.`, 'warning');
            return;
        }
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        data.query = query;

        queryCount++;
        if (data.confidence > 0) totalConfidence += data.confidence;
        if (data.latency > 0) totalLatency += data.latency;
        updateStats();

        const botHtml = formatBotResponse(data);
        appendMessage('system', botHtml);
        renderHistory();

        if (ttsEnabled) speakRaw(data.answer);

        // Refresh usage bar after each query
        refreshUsageBar();

    } catch (err) {
        removeTyping();
        console.error(err);
        appendMessage('system', `<div class="message-text"><p style="color:var(--danger)">&#x26A0;&#xFE0F; Could not reach the server. Please check if the backend is running.</p></div>`);
        showToast('Connection failed', 'error');
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
});

// ===== SUGGESTION CHIPS =====
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        switchPanel('chat-panel');
        userInput.value = chip.getAttribute('data-query');
        chatForm.dispatchEvent(new Event('submit'));
    });
});

// ===== SIDEBAR =====
sidebarToggleBtn.addEventListener('click', () => sidebar.classList.toggle('collapsed'));
sidebarCloseBtn.addEventListener('click', () => sidebar.classList.add('collapsed'));
newChatBtn.addEventListener('click', () => { switchPanel('chat-panel'); startNewSession(); });
clearHistoryBtn.addEventListener('click', () => {
    if (confirm('Clear all chat history?')) {
        sessions = {};
        saveSessions();
        startNewSession();
        showToast('History cleared', 'info');
    }
});
historySearchInput.addEventListener('input', () => renderHistory(historySearchInput.value));

// ===== MODE TOGGLE =====
const modeToggleBtn = document.getElementById('mode-toggle-btn');
const modeLabel = document.getElementById('mode-label');
modeToggleBtn.addEventListener('click', () => {
    currentMode = currentMode === 'clinical' ? 'patient' : 'clinical';
    modeLabel.textContent = currentMode === 'clinical' ? 'Clinical' : 'Patient';
    modeToggleBtn.classList.toggle('active', currentMode === 'clinical');
    showToast(`${currentMode === 'clinical' ? 'Clinical' : 'Patient'} mode activated`, 'info');
});

// ===== THEME =====
function loadTheme() {
    const saved = localStorage.getItem('cancerAI_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    themeToggleBtn.textContent = saved === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
}
themeToggleBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('cancerAI_theme', next);
    themeToggleBtn.textContent = next === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
    showToast(`${next === 'dark' ? 'Dark' : 'Light'} mode activated`, 'info');
});

// ===== VOICE INPUT =====
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { showToast('Speech recognition not supported', 'error'); return null; }
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.onresult = (e) => {
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) transcript += e.results[i][0].transcript;
        userInput.value = transcript;
        userInput.dispatchEvent(new Event('input'));
    };
    rec.onend = () => stopVoiceRecording();
    rec.onerror = (e) => { console.error('Speech error:', e.error); stopVoiceRecording(); if (e.error !== 'aborted') showToast('Voice error: ' + e.error, 'error'); };
    return rec;
}

function startVoiceRecording() {
    if (!recognition) recognition = setupSpeechRecognition();
    if (!recognition) return;
    try {
        recognition.start();
        isRecording = true;
        voiceRecordingBar.classList.add('active');
        voiceMicBtn.classList.add('recording');
        voiceInputBtn.classList.add('active');
    } catch (e) { console.error(e); }
}

function stopVoiceRecording() {
    if (recognition && isRecording) { try { recognition.stop(); } catch {} }
    isRecording = false;
    voiceRecordingBar.classList.remove('active');
    voiceMicBtn.classList.remove('recording');
    voiceInputBtn.classList.remove('active');
}

voiceInputBtn.addEventListener('click', () => isRecording ? stopVoiceRecording() : startVoiceRecording());
voiceMicBtn.addEventListener('click', () => isRecording ? stopVoiceRecording() : startVoiceRecording());
stopRecordingBtn.addEventListener('click', () => { stopVoiceRecording(); if (userInput.value.trim()) chatForm.dispatchEvent(new Event('submit')); });

// ===== TEXT-TO-SPEECH =====
ttsToggleBtn.addEventListener('click', () => {
    ttsEnabled = !ttsEnabled;
    ttsToggleBtn.classList.toggle('active', ttsEnabled);
    showToast(ttsEnabled ? 'Auto read-aloud enabled' : 'Auto read-aloud disabled', 'info');
});

function speakRaw(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 0.95;
    utter.pitch = 1;
    window.speechSynthesis.speak(utter);
}

window.speakText = function(btn) {
    const text = btn.getAttribute('data-text');
    if (text) speakRaw(text);
};

// ===== EXPORT =====
exportBtn.addEventListener('click', () => {
    if (!sessions[currentSessionId]) return;
    const session = sessions[currentSessionId];
    let text = `OncoGraph AI - Chat Export\n${'='.repeat(40)}\nSession: ${session.title}\nDate: ${new Date(session.createdAt).toLocaleString()}\n${'='.repeat(40)}\n\n`;
    session.messages.forEach(msg => {
        const role = msg.role === 'user' ? 'YOU' : 'AI';
        const content = msg.role === 'user' ? msg.text : msg.html.replace(/<[^>]*>/g, '');
        text += `[${role}]\n${content}\n\n`;
    });
    text += `\n${'='.repeat(40)}\nExported on ${new Date().toLocaleString()}\nDisclaimer: For clinical decision support only.\n`;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `oncograph-ai-chat-${session.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Chat exported successfully', 'success');
});

// ===== STATS =====
function updateStats() {
    document.getElementById('stat-queries').textContent = queryCount;
    document.getElementById('stat-avg-conf').textContent = queryCount > 0 ? (totalConfidence / queryCount * 100).toFixed(1) + '%' : '—';
    document.getElementById('stat-avg-latency').textContent = queryCount > 0 ? (totalLatency / queryCount).toFixed(2) + 's' : '—';
    document.getElementById('stat-sessions').textContent = Object.keys(sessions).length;
}

// ===== TOASTS =====
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== IMAGE UPLOAD =====
imageUploadBtn.addEventListener('click', () => imageFileInput.click());
imageFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { showToast('Please select an image file', 'error'); return; }
    if (file.size > 5 * 1024 * 1024) { showToast('Image must be under 5MB', 'error'); return; }
    const reader = new FileReader();
    reader.onload = (ev) => {
        pendingImageDataUrl = ev.target.result;
        imagePreviewImg.src = pendingImageDataUrl;
        imagePreviewContainer.classList.add('active');
        showToast('Image attached', 'success');
    };
    reader.readAsDataURL(file);
    imageFileInput.value = '';
});
imagePreviewRemove.addEventListener('click', () => {
    pendingImageDataUrl = null;
    imagePreviewContainer.classList.remove('active');
    imagePreviewImg.src = '';
});

// ===== LIGHTBOX =====
window.openLightbox = function(src) {
    lightboxImg.src = src;
    lightbox.classList.add('active');
};
lightboxClose.addEventListener('click', () => lightbox.classList.remove('active'));
lightbox.addEventListener('click', (e) => { if (e.target === lightbox) lightbox.classList.remove('active'); });
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        lightbox.classList.remove('active');
        closeProfileModal();
        closeSubscriptionModal();
    }
});


// ═══════════════════════════════════════════════════════
// KNOWLEDGE GRAPH PANEL
// ═══════════════════════════════════════════════════════
function setupGraphPanel() {
    const graphRunBtn = document.getElementById('graph-run-btn');
    graphRunBtn.addEventListener('click', runGraphQuery);

    document.querySelectorAll('.graph-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.getElementById('graph-query-type').value = chip.getAttribute('data-type');
            document.getElementById('graph-entity-input').value = chip.getAttribute('data-id');
            runGraphQuery();
        });
    });
}

async function loadGraphStats() {
    try {
        const resp = await fetch(API_URL + '/graph/stats', { headers: getAuthHeaders() });
        if (!resp.ok) return;
        const data = await resp.json();
        const bar = document.getElementById('graph-stats-bar');
        bar.innerHTML = `
            <div class="gs-item"><span class="gs-value">${data.total_nodes}</span><span class="gs-label">Total Nodes</span></div>
            <div class="gs-item"><span class="gs-value">${data.total_edges}</span><span class="gs-label">Total Edges</span></div>
            ${Object.entries(data.node_types || {}).map(([k, v]) => `<div class="gs-item"><span class="gs-value">${v}</span><span class="gs-label">${k}</span></div>`).join('')}
        `;
        drawGraphVisualization();
    } catch (e) {
        console.log('Graph stats not available (backend offline)');
    }
}

async function runGraphQuery() {
    const queryType = document.getElementById('graph-query-type').value;
    const entityInput = document.getElementById('graph-entity-input').value.trim();
    if (!entityInput) { showToast('Enter an entity ID', 'error'); return; }

    const graphRunBtn = document.getElementById('graph-run-btn');
    graphRunBtn.disabled = true;
    graphRunBtn.textContent = 'Querying...';

    try {
        const body = { query_type: queryType };
        if (queryType === 'therapies' || queryType === 'profile' || queryType === 'search' || queryType === 'path') body.mutation_id = entityInput;
        if (queryType === 'toxicities') body.drug_id = entityInput;
        if (queryType === 'biomarkers') body.cancer_id = entityInput;
        if (queryType === 'path') body.cancer_id = entityInput.split(',')[1] || 'NSCLC';

        const resp = await fetch(API_URL + '/graph/traverse', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (resp.status === 403) { showToast('Upgrade to Clinical plan to use Knowledge Graph.', 'error'); openSubscriptionModal(); return; }
        const data = await resp.json();
        renderGraphResults(queryType, data);
    } catch (e) {
        document.getElementById('graph-results').innerHTML = `<div class="empty-state"><p style="color:var(--danger)">Failed to query graph. Is the backend running?</p></div>`;
    } finally {
        graphRunBtn.disabled = false;
        graphRunBtn.textContent = '&#x1F50D; Traverse Graph';
    }
}

function renderGraphResults(queryType, data) {
    const container = document.getElementById('graph-results');
    if (data.error) { container.innerHTML = `<div class="empty-state"><p style="color:var(--danger)">${escapeHtml(data.error)}</p></div>`; return; }
    let html = '';
    const results = data.results || data.path || [];

    if (queryType === 'therapies' && Array.isArray(results)) {
        html += `<div style="margin-bottom:12px;font-size:.85rem;color:var(--text-muted)">Found ${results.length} targeted therapy option(s) for <strong style="color:var(--primary)">${escapeHtml(data.mutation_id || '')}</strong></div>`;
        results.forEach(t => { html += `<div class="result-card"><div class="rc-title"><span class="rc-badge drug">${escapeHtml(t.drug_class)}</span>${escapeHtml(t.drug_label)}</div><div class="rc-meta"><strong>Evidence:</strong> ${escapeHtml(t.evidence)}</div></div>`; });
    } else if (queryType === 'toxicities' && Array.isArray(results)) {
        html += `<div style="margin-bottom:12px;font-size:.85rem;color:var(--text-muted)">Found ${results.length} known toxicity(ies) for <strong style="color:var(--primary)">${escapeHtml(data.drug_id || '')}</strong></div>`;
        results.forEach(t => { html += `<div class="result-card"><div class="rc-title"><span class="rc-badge toxicity">CTCAE</span>${escapeHtml(t.toxicity_label)}</div></div>`; });
    } else if (queryType === 'biomarkers' && Array.isArray(results)) {
        html += `<div style="margin-bottom:12px;font-size:.85rem;color:var(--text-muted)">Found ${results.length} biomarker(s) for <strong style="color:var(--primary)">${escapeHtml(data.cancer_id || '')}</strong></div>`;
        results.forEach(b => { html += `<div class="result-card"><div class="rc-title"><span class="rc-badge biomarker">Biomarker</span>${escapeHtml(b.biomarker_label)}</div><div class="rc-meta">ID: <code>${escapeHtml(b.biomarker_id)}</code></div></div>`; });
    } else if (queryType === 'profile' && data.results) {
        const p = data.results;
        html += `<div style="margin-bottom:12px;font-size:.85rem;color:var(--text-muted)">Full genomic patient profile</div>`;
        html += `<div class="result-card"><div class="rc-title">Mutations (${p.mutations?.length || 0})</div><div class="rc-meta">${(p.mutations || []).map(m => `<span class="rc-badge mutation">${escapeHtml(m.label)}</span>`).join(' ')}</div></div>`;
        html += `<div class="result-card"><div class="rc-title">Targeted Therapies (${p.therapies?.length || 0})</div><div class="rc-meta">${(p.therapies || []).map(t => `<span class="rc-badge drug">${escapeHtml(t.drug_label)}</span>`).join(' ')}</div></div>`;
        if (p.toxicities?.length > 0) { html += `<div class="result-card"><div class="rc-title">Known Toxicities (${p.toxicities.length})</div><div class="rc-meta">${p.toxicities.map(t => `<span class="rc-badge toxicity">${escapeHtml(t.toxicity_label)}</span>`).join(' ')}</div></div>`; }
    } else if (queryType === 'search' && Array.isArray(results)) {
        results.forEach(r => { html += `<div class="result-card"><div class="rc-title"><span class="rc-badge biomarker">${escapeHtml(r.type)}</span>${escapeHtml(r.label)}</div><div class="rc-meta">ID: <code>${escapeHtml(r.id)}</code></div></div>`; });
    } else {
        html = `<div class="empty-state"><p>No results found</p></div>`;
    }
    container.innerHTML = html;
}

async function drawGraphVisualization() {
    const canvas = document.getElementById('graph-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 400;

    try {
        const resp = await fetch(API_URL + '/graph/export', { headers: getAuthHeaders() });
        if (!resp.ok) return;
        const data = await resp.json();

        const nodeTypeColors = {
            'CANCER_TYPE': '#f87171', 'BIOMARKER': '#34d399', 'DRUG': '#818cf8',
            'PROTOCOL': '#fbbf24', 'TOXICITY': '#fb7185', 'STAGING': '#38bdf8', 'EMERGENCY': '#ef4444'
        };

        const nodes = data.nodes || [];
        const edges = data.edges || [];
        const positions = {};
        const cx = canvas.width / 2, cy = canvas.height / 2;
        nodes.forEach((n, i) => {
            const angle = (i / nodes.length) * Math.PI * 2;
            const radius = 120 + Math.random() * 60;
            positions[n.id] = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
        });

        for (let iter = 0; iter < 10; iter++) {
            nodes.forEach((a, i) => {
                nodes.forEach((b, j) => {
                    if (i >= j) return;
                    const pa = positions[a.id], pb = positions[b.id];
                    const dx = pb.x - pa.x, dy = pb.y - pa.y;
                    const dist = Math.max(Math.hypot(dx, dy), 1);
                    const force = 800 / (dist * dist);
                    pa.x -= (dx / dist) * force; pa.y -= (dy / dist) * force;
                    pb.x += (dx / dist) * force; pb.y += (dy / dist) * force;
                });
            });
            edges.forEach(e => {
                const pa = positions[e.source], pb = positions[e.target];
                if (!pa || !pb) return;
                const dx = pb.x - pa.x, dy = pb.y - pa.y;
                const dist = Math.hypot(dx, dy);
                const force = dist * 0.005;
                pa.x += (dx / dist) * force; pa.y += (dy / dist) * force;
                pb.x -= (dx / dist) * force; pb.y -= (dy / dist) * force;
            });
            nodes.forEach(n => {
                const p = positions[n.id];
                p.x += (cx - p.x) * 0.01; p.y += (cy - p.y) * 0.01;
                p.x = Math.max(30, Math.min(canvas.width - 30, p.x));
                p.y = Math.max(30, Math.min(canvas.height - 30, p.y));
            });
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        edges.forEach(e => {
            const pa = positions[e.source], pb = positions[e.target];
            if (!pa || !pb) return;
            ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y);
            ctx.strokeStyle = 'rgba(129,140,248,0.15)'; ctx.lineWidth = 0.8; ctx.stroke();
        });
        nodes.forEach(n => {
            const p = positions[n.id];
            const color = nodeTypeColors[n.type] || '#94a3b8';
            ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
            ctx.fillStyle = color; ctx.fill();
            ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 1; ctx.stroke();
            if (nodes.length < 60) {
                ctx.font = '8px Inter, sans-serif'; ctx.fillStyle = 'rgba(148,163,184,0.7)';
                ctx.textAlign = 'center'; ctx.fillText(n.id.replace(/_/g, ' ').substring(0, 16), p.x, p.y + 14);
            }
        });
    } catch (e) {
        ctx.font = '14px Inter, sans-serif'; ctx.fillStyle = '#64748b'; ctx.textAlign = 'center';
        ctx.fillText('Knowledge graph visualization (connect backend to render)', canvas.width / 2, canvas.height / 2);
    }
}


// ═══════════════════════════════════════════════════════
// TUMOR BOARD PANEL
// ═══════════════════════════════════════════════════════
const TB_PRESETS = {
    nsclc_egfr: { query: '55-year-old male, Stage IV NSCLC, EGFR L858R mutation detected on NGS, currently on Osimertinib, presenting with new CNS metastases.', mutations: 'EGFR_L858R', cancer_type: 'NSCLC', symptoms: 'headache, vision changes', medications: '', stage: 'Stage IV' },
    breast_her2: { query: '48-year-old female, HER2-positive metastatic breast cancer, progressed on Trastuzumab+Pertuzumab. Currently taking ketoconazole for fungal infection.', mutations: 'HER2_AMP', cancer_type: 'BREAST_CANCER', symptoms: 'fatigue, bone pain', medications: 'ketoconazole', stage: 'Stage IV' },
    crc_msi: { query: '62-year-old male, metastatic colorectal cancer, MSI-High/dMMR confirmed. Failed FOLFOX. Evaluating immunotherapy options.', mutations: 'MSI_H', cancer_type: 'CRC', symptoms: 'abdominal pain, weight loss', medications: '', stage: 'Stage IV' },
    melanoma_braf: { query: '41-year-old female, metastatic cutaneous melanoma, BRAF V600E mutation, treatment-naive. Assess targeted vs immunotherapy options.', mutations: 'BRAF_V600E', cancer_type: 'MELANOMA', symptoms: 'growing skin lesion', medications: '', stage: 'Stage III' }
};

function setupTumorBoardPanel() {
    document.getElementById('tb-run-btn').addEventListener('click', runTumorBoard);
    document.querySelectorAll('.tb-preset-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const preset = TB_PRESETS[chip.getAttribute('data-preset')];
            if (!preset) return;
            document.getElementById('tb-query').value = preset.query;
            document.getElementById('tb-mutations').value = preset.mutations;
            document.getElementById('tb-cancer-type').value = preset.cancer_type;
            document.getElementById('tb-symptoms').value = preset.symptoms;
            document.getElementById('tb-medications').value = preset.medications;
            document.getElementById('tb-stage').value = preset.stage;
            showToast('Preset loaded', 'info');
        });
    });
}

async function runTumorBoard() {
    const query = document.getElementById('tb-query').value.trim();
    if (!query) { showToast('Enter a clinical question', 'error'); return; }
    const tbRunBtn = document.getElementById('tb-run-btn');
    tbRunBtn.disabled = true;
    tbRunBtn.textContent = 'Analyzing...';

    const mutations = document.getElementById('tb-mutations').value.split(',').map(s => s.trim()).filter(Boolean);
    const symptoms = document.getElementById('tb-symptoms').value.split(',').map(s => s.trim()).filter(Boolean);
    const coMeds = document.getElementById('tb-medications').value.split(',').map(s => s.trim()).filter(Boolean);

    try {
        const resp = await fetch(API_URL + '/tumor-board/analyze', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ query, mutations, symptoms, co_medications: coMeds, cancer_type: document.getElementById('tb-cancer-type').value, stage: document.getElementById('tb-stage').value })
        });
        if (resp.status === 403) { showToast('Tumor Board requires Enterprise plan.', 'error'); openSubscriptionModal(); return; }
        const data = await resp.json();
        renderTumorBoardResults(data);
    } catch (e) {
        document.getElementById('tb-results').innerHTML = `<div class="empty-state"><p style="color:var(--danger)">Failed to run tumor board analysis</p></div>`;
    } finally {
        tbRunBtn.disabled = false;
        tbRunBtn.innerHTML = '&#x1FA7A; Run Tumor Board Analysis';
    }
}

function renderTumorBoardResults(data) {
    const container = document.getElementById('tb-results');
    if (data.error) { container.innerHTML = `<div class="empty-state"><p style="color:var(--danger)">${escapeHtml(data.error)}</p></div>`; return; }
    const AGENT_ICONS = {
        'Triage & Emergency Agent': { icon: '&#x1F6A8;', bg: 'rgba(248,113,113,.15)' },
        'Genomic & Biomarker Specialist Agent': { icon: '&#x1F9EC;', bg: 'rgba(52,211,153,.15)' },
        'Clinical Trial Matchmaker Agent': { icon: '&#x1F50D;', bg: 'rgba(129,140,248,.15)' },
        'Pharmacovigilance & Drug Interaction Agent': { icon: '&#x1F48A;', bg: 'rgba(251,191,36,.15)' },
    };
    let html = '';
    (data.agent_reports || []).forEach(report => {
        const agentInfo = AGENT_ICONS[report.agent] || { icon: '&#x1F916;', bg: 'var(--glass-bg)' };
        html += `<div class="agent-card"><div class="agent-header"><div class="agent-icon" style="background:${agentInfo.bg}">${agentInfo.icon}</div><div class="agent-name">${escapeHtml(report.agent)}</div></div><div class="agent-body">`;
        if (report.agent.includes('Triage')) {
            const color = report.triage_level === 'RED' ? 'var(--danger)' : report.triage_level === 'YELLOW' ? 'var(--warning)' : 'var(--success)';
            html += `<p><strong>Level:</strong> <span style="color:${color};font-weight:700">${escapeHtml(report.triage_level || 'GREEN')}</span> &mdash; ${escapeHtml(report.title || '')}</p><p>${escapeHtml(report.action || '')}</p>`;
        } else if (report.agent.includes('Genomic')) {
            html += `<p><strong>Mutations Detected:</strong> ${(report.mutations_detected || []).map(m => `<span class="rc-badge mutation">${escapeHtml(m.label || m.id)}</span>`).join(' ') || 'None'}</p>`;
            if (report.therapies?.length > 0) { html += '<ul>'; report.therapies.forEach(t => { html += `<li><strong>${escapeHtml(t.drug_label)}</strong> (${escapeHtml(t.drug_class)}) &mdash; ${escapeHtml(t.evidence)}</li>`; }); html += '</ul>'; }
            html += `<p>${escapeHtml(report.recommendation || '')}</p>`;
        } else if (report.agent.includes('Trial')) {
            html += `<p><strong>Matched Trials:</strong> ${report.total_matches || 0}</p>`;
            if (report.matched_trials?.length > 0) { html += '<ul>'; report.matched_trials.forEach(t => { html += `<li><strong>${escapeHtml(t.nct_id)}</strong> &mdash; ${escapeHtml(t.title)} (${escapeHtml(t.phase)}, ${escapeHtml(t.status)})</li>`; }); html += '</ul>'; }
        } else if (report.agent.includes('Pharmacovigilance')) {
            html += `<p><strong>Drug Interactions:</strong> ${report.interaction_count || 0}</p>`;
            if (report.drug_interactions?.length > 0) { html += '<ul>'; report.drug_interactions.forEach(i => { html += `<li><strong style="color:var(--danger)">${escapeHtml(i.risk)}</strong>: ${escapeHtml(i.drug)} + ${escapeHtml(i.co_medication)} (${escapeHtml(i.type)})</li>`; }); html += '</ul>'; }
            if (report.known_toxicities?.length > 0) { html += `<p><strong>Known Toxicities:</strong></p><ul>`; report.known_toxicities.forEach(t => { html += `<li>${escapeHtml(t.toxicity_label)}</li>`; }); html += '</ul>'; }
            html += `<p>${escapeHtml(report.recommendation || '')}</p>`;
        }
        html += `</div></div>`;
    });

    if (data.consensus) {
        const c = data.consensus;
        const triageColor = c.triage_level === 'RED' ? 'red' : c.triage_level === 'YELLOW' ? 'yellow' : 'green';
        html += `<div class="consensus-card"><h3>&#x1F3AF; Tumor Board Consensus Report</h3><div class="consensus-grid">
            <div class="consensus-metric"><span class="cm-value ${triageColor}">${escapeHtml(c.triage_level || 'GREEN')}</span><span class="cm-label">Triage Level</span></div>
            <div class="consensus-metric"><span class="cm-value blue">${c.actionable_mutations || 0}</span><span class="cm-label">Mutations</span></div>
            <div class="consensus-metric"><span class="cm-value green">${c.targeted_therapies_available || 0}</span><span class="cm-label">Therapies</span></div>
            <div class="consensus-metric"><span class="cm-value blue">${c.eligible_clinical_trials || 0}</span><span class="cm-label">Clinical Trials</span></div>
            <div class="consensus-metric"><span class="cm-value ${c.drug_interactions_detected > 0 ? 'red' : 'green'}">${c.drug_interactions_detected || 0}</span><span class="cm-label">Drug Interactions</span></div>
        </div><div class="consensus-recommendation"><strong>Recommendation:</strong> ${escapeHtml(c.overall_recommendation || '')}</div></div>`;
    }
    if (data.latency) html += `<div class="metrics" style="margin-top:12px"><span class="metric-item">&#x23F1;&#xFE0F; Analysis: ${data.latency.toFixed(3)}s</span></div>`;
    container.innerHTML = html;
}


// ═══════════════════════════════════════════════════════
// FEDERATED LEARNING PANEL
// ═══════════════════════════════════════════════════════
function setupFederatedPanel() {
    document.getElementById('fed-run-btn').addEventListener('click', runFederatedTraining);
    document.getElementById('fed-status-btn').addEventListener('click', loadFederatedStatus);
    loadFederatedStatus();
}

async function loadFederatedStatus() {
    try {
        const resp = await fetch(API_URL + '/federated/status', { headers: getAuthHeaders() });
        if (!resp.ok) return;
        const data = await resp.json();
        renderHospitalCards(data.hospitals || []);
    } catch { console.log('Federated status not available'); }
}

function renderHospitalCards(hospitals) {
    const container = document.getElementById('fed-hospitals');
    const HOSPITAL_COLORS = ['rgba(129,140,248,.15)', 'rgba(52,211,153,.15)', 'rgba(251,191,36,.15)'];
    const HOSPITAL_ICONS = ['&#x1F3E5;', '&#x1F3EB;', '&#x1F3E8;'];
    container.innerHTML = hospitals.map((h, i) => `
        <div class="hospital-card">
            <div class="hc-header">
                <div class="hc-icon" style="background:${HOSPITAL_COLORS[i % 3]}">${HOSPITAL_ICONS[i % 3]}</div>
                <div><div class="hc-name">${escapeHtml(h.name)}</div><div class="hc-focus">${escapeHtml(h.focus)}</div></div>
            </div>
            <div class="hc-stats">
                <div class="hc-stat"><span class="hc-stat-value">${h.samples?.toLocaleString() || '0'}</span><span class="hc-stat-label">Samples</span></div>
                <div class="hc-stat"><span class="hc-stat-value">${h.rounds_completed || 0}</span><span class="hc-stat-label">Rounds</span></div>
                <div class="hc-stat"><span class="hc-stat-value">${h.latest_loss != null ? h.latest_loss.toFixed(4) : '—'}</span><span class="hc-stat-label">Loss</span></div>
                <div class="hc-stat"><span class="hc-stat-value">${escapeHtml(h.id?.substring(0, 8) || '')}</span><span class="hc-stat-label">Node ID</span></div>
            </div>
        </div>
    `).join('');
}

async function runFederatedTraining() {
    const fedRunBtn = document.getElementById('fed-run-btn');
    fedRunBtn.disabled = true;
    fedRunBtn.textContent = 'Training...';
    const nRounds = parseInt(document.getElementById('fed-rounds').value) || 3;
    const localEpochs = parseInt(document.getElementById('fed-epochs').value) || 5;
    try {
        const resp = await fetch(API_URL + '/federated/train', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ n_rounds: nRounds, local_epochs: localEpochs })
        });
        if (resp.status === 403) { showToast('Federated Learning requires Enterprise plan.', 'error'); openSubscriptionModal(); return; }
        const data = await resp.json();
        renderFederatedResults(data);
        if (data.hospitals) renderHospitalCards(data.hospitals);
    } catch { document.getElementById('fed-results').innerHTML = `<div class="empty-state"><p style="color:var(--danger)">Failed to run federated training</p></div>`; }
    finally { fedRunBtn.disabled = false; fedRunBtn.innerHTML = '&#x1F680; Launch Federated Training'; }
}

function renderFederatedResults(data) {
    const container = document.getElementById('fed-results');
    if (data.error) { container.innerHTML = `<div class="empty-state"><p style="color:var(--danger)">${escapeHtml(data.error)}</p></div>`; return; }
    let html = `<div style="margin-bottom:16px;font-size:.85rem;color:var(--text-muted)"><strong>Completed:</strong> ${data.total_rounds} rounds | <strong>Time:</strong> ${data.total_training_time_seconds}s | <strong>Status:</strong> <span style="color:var(--success)">${escapeHtml(data.status || 'COMPLETE')}</span></div>`;
    (data.rounds || []).forEach(round => {
        html += `<div class="training-round"><div class="tr-header">Round ${round.round} of ${data.total_rounds}</div><div class="tr-body">${(round.hospital_reports || []).map(hr => `<div><strong>${escapeHtml(hr.hospital_name)}</strong><br>Loss: ${hr.loss_start?.toFixed(4)} → ${hr.loss_end?.toFixed(4)} (↓${hr.loss_improvement}%)</div>`).join('')}</div></div>`;
    });
    html += `<div class="privacy-badge">&#x1F512; ${escapeHtml(data.privacy_guarantee || 'No patient data was exchanged between hospital nodes.')}</div>`;
    container.innerHTML = html;
}


// ═══════════════════════════════════════════════════════
// ML PROGNOSIS PANEL
// ═══════════════════════════════════════════════════════
function setupMLPanel() {
    document.getElementById('ml-predict-btn').addEventListener('click', runMLPrediction);
}

async function runMLPrediction() {
    const predictBtn = document.getElementById('ml-predict-btn');
    predictBtn.disabled = true;
    predictBtn.textContent = 'Running ML inference...';
    const age = parseInt(document.getElementById('ml-age').value) || 55;
    const tumorSize = parseFloat(document.getElementById('ml-tumor-size').value) || 3.5;
    const lymphNodes = parseInt(document.getElementById('ml-lymph-nodes').value) || 0;
    const biomarkerId = document.getElementById('ml-biomarker').value;
    const symptomCount = parseInt(document.getElementById('ml-symptom-count').value) || 2;

    try {
        const resp = await fetch(API_URL + '/diagnostics/predict', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ age, tumor_size: tumorSize, lymph_nodes: lymphNodes, biomarker_id: biomarkerId, symptom_count: symptomCount })
        });
        if (resp.status === 403) { showToast('ML Prognosis requires Clinical plan.', 'error'); openSubscriptionModal(); return; }
        const data = await resp.json();
        if (data.success && data.results) {
            renderMLResults(data.results);
        } else {
            showToast(data.message || 'ML Prediction failed', 'error');
        }
    } catch { document.getElementById('ml-results').innerHTML = `<div class="empty-state"><p style="color:var(--danger)">Failed to run ML prediction. Check API connection.</p></div>`; }
    finally { predictBtn.disabled = false; predictBtn.innerHTML = '&#x1F5A5;&#xFE0F; Run Prognosis Prediction'; }
}

function renderMLResults(res) {
    const container = document.getElementById('ml-results');
    let html = `
        <div class="ml-results-grid">
            <div class="ml-card-result">
                <h3>&#x1F4CA; Random Forest Malignancy Probability</h3>
                <div class="ml-prob-bar"><div class="ml-prob-row"><span>Low Risk / Benign</span><strong>${res.probabilities.low.toFixed(1)}%</strong></div><div class="ml-prob-track"><div class="ml-prob-fill low" style="width: ${res.probabilities.low}%"></div></div></div>
                <div class="ml-prob-bar"><div class="ml-prob-row"><span>Moderate Risk / Localized</span><strong>${res.probabilities.moderate.toFixed(1)}%</strong></div><div class="ml-prob-track"><div class="ml-prob-fill moderate" style="width: ${res.probabilities.moderate}%"></div></div></div>
                <div class="ml-prob-bar"><div class="ml-prob-row"><span>High Risk / Metastatic</span><strong>${res.probabilities.high.toFixed(1)}%</strong></div><div class="ml-prob-track"><div class="ml-prob-fill high" style="width: ${res.probabilities.high}%"></div></div></div>
                <div class="consensus-recommendation" style="margin-top:16px; border-left: 4px solid var(--${res.color_theme}); padding: 8px 12px; background: rgba(255,255,255,0.02);">
                    <strong>Risk Classification:</strong> <span style="text-transform: uppercase; font-weight:700; color: var(--${res.color_theme})">${res.prediction_label}</span><br>
                    <p style="font-size:0.8rem; margin-top:4px; line-height:1.4;">${escapeHtml(res.clinical_notes)}</p>
                </div>
            </div>
            <div class="ml-card-result">
                <h3>&#x1F525; Local Gini Feature Importance</h3>
                ${Object.entries(res.feature_importance).map(([feature, val]) => `
                    <div class="ml-fi-item">
                        <div class="ml-fi-label">${escapeHtml(feature)}</div>
                        <div class="ml-fi-bar-container"><div class="ml-fi-bar"><div class="ml-fi-fill" style="width: ${val}%"></div></div><span class="ml-fi-value">${val.toFixed(1)}%</span></div>
                    </div>
                `).join('')}
            </div>
        </div>`;
    container.innerHTML = html;
}

// ===== BOOT =====
init();
