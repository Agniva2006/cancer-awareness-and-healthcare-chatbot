const API_URL = "https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/ask";

const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

function appendMessage(role, contentHTML) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '🧬';
    
    msgDiv.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="message-content">
            ${contentHTML}
        </div>
    `;
    
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system typing';
    msgDiv.id = 'typing-indicator-msg';
    
    msgDiv.innerHTML = `
        <div class="avatar">🧬</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator-msg');
    if (indicator) {
        indicator.remove();
    }
}

function formatBotResponse(data) {
    let html = `<p>${data.answer.replace(/\n/g, '<br>')}</p>`;
    
    if (data.sources && data.sources.length > 0) {
        html += `
            <div class="sources-container">
                <div class="sources-title">Sources Consulted</div>
                <div>
                    ${data.sources.map(src => `<span class="source-tag">${src}</span>`).join('')}
                </div>
            </div>
        `;
    }
    
    if (data.confidence || data.latency) {
        html += `<div class="metrics">`;
        if (data.confidence > 0) {
            html += `<div class="metric-item">🎯 Conf: ${data.confidence.toFixed(2)}</div>`;
        }
        if (data.latency > 0) {
            html += `<div class="metric-item">⏱️ ${(data.latency).toFixed(2)}s</div>`;
        }
        html += `</div>`;
    }
    
    if (data.disclaimer) {
        html += `<span class="disclaimer-text">${data.disclaimer}</span>`;
    }
    
    return html;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;
    
    // Add user message
    appendMessage('user', `<p>${query}</p>`);
    
    // Clear input & disable button
    userInput.value = '';
    sendBtn.disabled = true;
    
    showTypingIndicator();
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });
        
        removeTypingIndicator();
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        appendMessage('system', formatBotResponse(data));
        
    } catch (error) {
        removeTypingIndicator();
        console.error("Fetch Error:", error);
        appendMessage('system', `<p style="color: var(--danger)">Connection error. Please try again later. Ensure the backend URL is reachable and CORS is enabled if needed.</p>`);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
});
