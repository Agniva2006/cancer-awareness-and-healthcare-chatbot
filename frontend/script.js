// ===== CONFIGURATION =====
const API_URL = "https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/ask";
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
let pendingImageDataUrl = null; // attached image data URL

// ===== INIT =====
function init() {
    loadSessions();
    loadTheme();
    startNewSession();
    setupParticles();
    setupTextareaAutoResize();
    updateStats();
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

            // Draw connections
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

// ===== SESSION MANAGEMENT (localStorage) =====
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
        <div class="avatar bot-avatar">🧬</div>
        <div class="message-bubble">
            <div class="message-text">
                <p>Hello! I'm your <strong>Cancer Information Assistant</strong>. I can help you understand symptoms, treatments, prevention methods, and more.</p>
                <p>Choose a topic below or type your question.</p>
            </div>
            <span class="disclaimer-badge">ℹ️ For informational purposes only. Always consult a doctor.</span>
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
        const timeStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' · ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
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
    const avatar = role === 'user' ? '👤' : '🧬';
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
        <div class="avatar bot-avatar">🧬</div>
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
    let answerHtml = data.answer
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\* /g, '\n<li>')
        .replace(/\n- /g, '\n<li>');

    // Wrap consecutive <li> in <ul>
    if (answerHtml.includes('<li>')) {
        answerHtml = answerHtml.replace(/((<li>.*?(?:\n|$))+)/g, '<ul>$1</ul>');
    }
    answerHtml = answerHtml.replace(/\n/g, '<br>');

    let html = `<div class="message-text"><p>${answerHtml}</p></div>`;

    if (data.sources && data.sources.length > 0) {
        html += `<div class="sources-container"><div class="sources-title">Sources Consulted</div><div>${data.sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}</div></div>`;
    }

    if (data.confidence > 0 || data.latency > 0) {
        html += `<div class="metrics">`;
        if (data.confidence > 0) html += `<span class="metric-item">🎯 ${(data.confidence * 100).toFixed(1)}%</span>`;
        if (data.latency > 0) html += `<span class="metric-item">⏱️ ${data.latency.toFixed(2)}s</span>`;
        html += `</div>`;
    }

    if (data.disclaimer) {
        html += `<span class="disclaimer-badge">⚠️ ${escapeHtml(data.disclaimer)}</span>`;
    }

    // TTS button
    html += `<button class="msg-tts-btn" onclick="speakText(this)" data-text="${escapeHtml(data.answer)}">🔊 Read Aloud</button>`;

    // Topic illustration
    const topicImg = detectTopicImage(data.query || '', data.answer || '', data.sources || []);
    if (topicImg) {
        html += `
            <div class="topic-illustration" onclick="openLightbox('${topicImg.src}')">
                <img src="${topicImg.src}" alt="${topicImg.label}" loading="lazy">
                <div class="illustration-label">${topicImg.label}</div>
            </div>`;
    }

    return html;
}

// ===== FORM SUBMIT =====
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    userMessageCount++;
    if (userMessageCount >= 1) suggestionsOverlay.classList.add('hidden');

    // Build user message HTML (with optional attached image)
    let userHtml = `<p>${escapeHtml(query)}</p>`;
    if (pendingImageDataUrl) {
        userHtml += `<div class="user-attached-image" onclick="openLightbox('${pendingImageDataUrl}')"><img src="${pendingImageDataUrl}" alt="Attached image"></div>`;
        pendingImageDataUrl = null;
        imagePreviewContainer.classList.remove('active');
    }
    appendMessage('user', userHtml);

    // Update session title from first message
    if (sessions[currentSessionId] && sessions[currentSessionId].title === 'New Conversation') {
        sessions[currentSessionId].title = query.length > 40 ? query.substring(0, 40) + '…' : query;
        saveSessions();
        renderHistory();
    }

    userInput.value = '';
    userInput.style.height = 'auto';
    charCount.textContent = `0 / ${MAX_CHARS}`;
    sendBtn.disabled = true;
    showTyping();

    try {
        const resp = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        removeTyping();
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        data.query = query; // attach for topic image detection

        queryCount++;
        if (data.confidence > 0) totalConfidence += data.confidence;
        if (data.latency > 0) totalLatency += data.latency;
        updateStats();

        const botHtml = formatBotResponse(data);
        appendMessage('system', botHtml);
        renderHistory();

        if (ttsEnabled) speakRaw(data.answer);
    } catch (err) {
        removeTyping();
        console.error(err);
        appendMessage('system', `<div class="message-text"><p style="color:var(--danger)">⚠️ Could not reach the server. Please check if the backend is running and CORS is enabled.</p></div>`);
        showToast('Connection failed', 'error');
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
});

// ===== SUGGESTION CHIPS =====
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        userInput.value = chip.getAttribute('data-query');
        chatForm.dispatchEvent(new Event('submit'));
    });
});

// ===== SIDEBAR =====
sidebarToggleBtn.addEventListener('click', () => sidebar.classList.toggle('collapsed'));
sidebarCloseBtn.addEventListener('click', () => sidebar.classList.add('collapsed'));
newChatBtn.addEventListener('click', startNewSession);
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

// ===== VOICE INPUT (Web Speech API) =====
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast('Speech recognition not supported in this browser', 'error');
        return null;
    }
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'en-US';

    rec.onresult = (e) => {
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) {
            transcript += e.results[i][0].transcript;
        }
        userInput.value = transcript;
        userInput.dispatchEvent(new Event('input'));
    };
    rec.onend = () => stopVoiceRecording();
    rec.onerror = (e) => {
        console.error('Speech error:', e.error);
        stopVoiceRecording();
        if (e.error !== 'aborted') showToast('Voice recognition error: ' + e.error, 'error');
    };
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
    if (recognition && isRecording) {
        try { recognition.stop(); } catch {}
    }
    isRecording = false;
    voiceRecordingBar.classList.remove('active');
    voiceMicBtn.classList.remove('recording');
    voiceInputBtn.classList.remove('active');
}

voiceInputBtn.addEventListener('click', () => isRecording ? stopVoiceRecording() : startVoiceRecording());
voiceMicBtn.addEventListener('click', () => isRecording ? stopVoiceRecording() : startVoiceRecording());
stopRecordingBtn.addEventListener('click', () => {
    stopVoiceRecording();
    if (userInput.value.trim()) chatForm.dispatchEvent(new Event('submit'));
});

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
    let text = `Cancer AI Assistant - Chat Export\n${'='.repeat(40)}\nSession: ${session.title}\nDate: ${new Date(session.createdAt).toLocaleString()}\n${'='.repeat(40)}\n\n`;

    session.messages.forEach(msg => {
        const role = msg.role === 'user' ? 'YOU' : 'AI';
        const content = msg.role === 'user' ? msg.text : msg.html.replace(/<[^>]*>/g, '');
        text += `[${role}]\n${content}\n\n`;
    });

    text += `\n${'='.repeat(40)}\nExported on ${new Date().toLocaleString()}\nDisclaimer: For informational purposes only. Always consult a doctor.\n`;

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cancer-ai-chat-${session.id}.txt`;
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

// ===== TOPIC IMAGE DETECTION =====
const TOPIC_IMAGES = [
    { keywords: ['lung', 'pulmonary', 'respiratory', 'breathing', 'cough'], src: 'images/lung_cancer.png', label: 'Lung Cancer Illustration' },
    { keywords: ['breast', 'mammogram', 'mammography'], src: 'images/breast_cancer.png', label: 'Breast Cancer Awareness' },
    { keywords: ['chemotherapy', 'chemo', 'drug', 'medication'], src: 'images/chemotherapy.png', label: 'Chemotherapy Overview' },
    { keywords: ['prevent', 'prevention', 'risk', 'lifestyle', 'diet', 'exercise', 'avoid'], src: 'images/prevention.png', label: 'Cancer Prevention' },
    { keywords: ['radiation', 'radiotherapy', 'x-ray', 'proton'], src: 'images/radiation.png', label: 'Radiation Therapy' },
    { keywords: ['cancer', 'tumor', 'cell', 'staging', 'screening', 'survival', 'palliative'], src: 'images/general.png', label: 'Cancer Awareness' }
];

function detectTopicImage(query, answer, sources) {
    const combined = (query + ' ' + answer + ' ' + sources.join(' ')).toLowerCase();
    for (const topic of TOPIC_IMAGES) {
        if (topic.keywords.some(kw => combined.includes(kw))) {
            return { src: topic.src, label: topic.label };
        }
    }
    return null;
}

// ===== IMAGE UPLOAD =====
imageUploadBtn.addEventListener('click', () => imageFileInput.click());

imageFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        showToast('Image must be under 5MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
        pendingImageDataUrl = ev.target.result;
        imagePreviewImg.src = pendingImageDataUrl;
        imagePreviewContainer.classList.add('active');
        showToast('Image attached', 'success');
    };
    reader.readAsDataURL(file);
    imageFileInput.value = ''; // reset so same file can be re-selected
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
lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) lightbox.classList.remove('active');
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightbox.classList.contains('active')) {
        lightbox.classList.remove('active');
    }
});

// ===== BOOT =====
init();
