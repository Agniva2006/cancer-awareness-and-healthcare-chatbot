// ===== CONFIGURATION =====
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';

const API_URL = isLocal 
    ? "http://127.0.0.1:8000" 
    : "https://cancer-awareness-and-healthcare-chatbot-n2wy.onrender.com";

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

// ===== UNRESTRICTED GUEST STATE (Enterprise Tier) =====
let currentUser = {
    username: "guest_clinician",
    email: "guest@oncograph.ai",
    full_name: "Guest Clinician",
    specialty: "Oncology",
    institution: "Global Medical Center",
    role: "admin",
    plan: "enterprise"
};
const authToken = "chatbot";

// ===== INIT =====
function init() {
    loadSessions();
    loadTheme();
    startNewSession();
    setupParticles();
    setupTextareaAutoResize();
    setupNavTabs();
    checkBackendHealth();
    setInterval(checkBackendHealth, 30000);
}

async function checkBackendHealth() {
    const statusDot = statusIndicator ? statusIndicator.querySelector('.dot') : null;
    const statusText = statusIndicator ? statusIndicator.querySelector('.status-text') : null;
    try {
        const resp = await fetch(API_URL + '/health', { method: 'GET' });
        if (resp.ok) {
            if (statusDot) statusDot.style.background = '#10b981';
            if (statusText) statusText.textContent = 'API Connected';
        } else {
            if (statusDot) statusDot.style.background = '#f59e0b';
            if (statusText) statusText.textContent = 'Waking Up...';
        }
    } catch {
        if (statusDot) statusDot.style.background = '#ef4444';
        if (statusText) statusText.textContent = 'Connecting...';
    }
}

// ══════════════════════════════════════════════════════
// AUTH BYPASS — Always Unlocked Enterprise Session
// ══════════════════════════════════════════════════════

function getAuthHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    };
}

function setupNavTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const panelId = tab.getAttribute('data-panel');
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
            submitChatMessage();
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
                <p>Hello! I'm <strong>Cancer Awareness Chatbot</strong> &mdash; I can share general information about cancer, prevention, screening, symptoms, and care.</p>
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
                <div class="triage-alert-title">${isRed ? '🚨 EMERGENCY TRIAGE ALERT' : '⚠️ CLINICAL ATTENTION RECOMMENDED'}</div>
                <div class="triage-alert-action">${escapeHtml(data.triage.action || '')}</div>
            </div>`;
    }

    let cleanAnswer = data.answer
        .replace(/\|/g, '')
        .replace(/---/g, '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    let answerHtml = cleanAnswer
        .replace(/\n\* /g, '<br>• ')
        .replace(/\n- /g, '<br>• ')
        .replace(/\n/g, '<br>');

    html += `<div class="message-text"><p>${answerHtml}</p></div>`;
    html += `<button class="msg-tts-btn" onclick="speakText(this)" data-text="${escapeHtml(data.answer)}">🔊 Read Aloud</button>`;

    return html;
}

// ===== SUBMIT CHAT MESSAGE =====
window.submitChatMessage = async function(queryOverride) {
    const query = (queryOverride !== undefined ? queryOverride : userInput.value).trim();
    if (!query) return;

    userMessageCount++;
    if (userMessageCount >= 1 && suggestionsOverlay) suggestionsOverlay.classList.add('hidden');

    let imagePayload = null;
    let userHtml = `<p>${escapeHtml(query)}</p>`;
    if (pendingImageDataUrl) {
        imagePayload = pendingImageDataUrl;
        userHtml += `<div class="user-attached-image" onclick="openLightbox('${pendingImageDataUrl}')"><img src="${pendingImageDataUrl}" alt="Attached image"></div>`;
        pendingImageDataUrl = null;
        if (imagePreviewContainer) imagePreviewContainer.classList.remove('active');
    }
    appendMessage('user', userHtml);

    if (sessions[currentSessionId] && sessions[currentSessionId].title === 'New Conversation') {
        sessions[currentSessionId].title = query.length > 40 ? query.substring(0, 40) + '...' : query;
        saveSessions();
        renderHistory();
    }

    userInput.value = '';
    userInput.style.height = 'auto';
    if (charCount) charCount.textContent = `0 / ${MAX_CHARS}`;
    if (sendBtn) sendBtn.disabled = true;
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

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        data.query = query;

        queryCount++;
        if (data.confidence > 0) totalConfidence += data.confidence;
        if (data.latency > 0) totalLatency += data.latency;
        const botHtml = formatBotResponse(data);
        appendMessage('system', botHtml);
        renderHistory();

        if (ttsEnabled) speakRaw(data.answer);

    } catch (err) {
        removeTyping();
        console.error('Chat error:', err);
        appendMessage('system', `<div class="message-text"><p style="color:var(--danger)">⚠️ Could not reach the server. Please check if the backend is running.</p></div>`);
        showToast('Connection failed. Retrying backend connection...', 'error');
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        userInput.focus();
    }
};

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitChatMessage();
});

// ===== SUGGESTION CHIPS =====
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        switchPanel('chat-panel');
        const q = chip.getAttribute('data-query');
        if (q) submitChatMessage(q);
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
    rec.onerror = (e) => { stopVoiceRecording(); };
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

voiceMicBtn.addEventListener('click', () => isRecording ? stopVoiceRecording() : startVoiceRecording());
stopRecordingBtn.addEventListener('click', () => { stopVoiceRecording(); if (userInput.value.trim()) submitChatMessage(); });

// ===== TEXT-TO-SPEECH =====


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
    let text = `Cancer Awareness Chatbot - Chat Export\n${'='.repeat(40)}\nSession: ${session.title}\nDate: ${new Date(session.createdAt).toLocaleString()}\n${'='.repeat(40)}\n\n`;
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
    }
});


// ═══════════════════════════════════════════════════════
// KNOWLEDGE GRAPH PANEL
// ═══════════════════════════════════════════════════════
init();
