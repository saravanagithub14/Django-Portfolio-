/**
 * Chat Widget Logic
 * Integrates with the Flask backend running at http://127.0.0.1:5000/chat
 */

(function() {
    // ⚙️ CONFIG
    const API_URL = "/chatbot/api/chat/";
    const BOT_NAME = "Saravana Perumal R.";

    // Inject HTML structure if not present
    const widgetHTML = `
        <button id="chat-fab" title="Chat with Saravana's AI">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        </button>
        <div id="chat-window">
            <div class="chat-header">
                <div class="chat-header-info">
                    <div class="chat-avatar">S</div>
                    <div>
                        <h4>${BOT_NAME}</h4>
                        <p>AI Practitioner (Online)</p>
                    </div>
                </div>
                <button class="close-chat">&times;</button>
            </div>
            <div id="chat-messages">
                <div class="message bot-message">Hi! I'm Saravana's AI assistant. Ask me anything about my experience, skills, or projects.</div>
            </div>
            <div class="chat-input-area">
                <div class="chat-input-wrap">
                    <input type="text" id="chat-input" placeholder="Type your message..." autocomplete="off">
                    <button id="chat-send">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', () => {
        const container = document.getElementById('chat-widget-container');
        if (container) {
            container.innerHTML = widgetHTML;
            initWidget();
        }
    });

    function initWidget() {
        const fab = document.getElementById('chat-fab');
        const window = document.getElementById('chat-window');
        const closeBtn = document.querySelector('.close-chat');
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send');
        const messages = document.getElementById('chat-messages');

        fab.addEventListener('click', () => {
            window.classList.toggle('active');
            if (window.classList.contains('active')) {
                input.focus();
            }
        });

        closeBtn.addEventListener('click', () => {
            window.classList.remove('active');
        });

        const sendMessage = async () => {
            const text = input.value.trim();
            if (!text) return;

            // Add user message
            addMessage('user', text);
            input.value = '';

            // Add typing indicator
            const typingId = 'typing-' + Date.now();
            const typingDiv = document.createElement('div');
            typingDiv.id = typingId;
            typingDiv.className = 'typing';
            typingDiv.textContent = 'Saravana is typing...';
            messages.appendChild(typingDiv);
            messages.scrollTop = messages.scrollHeight;

            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ message: text })
                });

                const rawText = await response.text();
                const typing = document.getElementById(typingId);
                if (typing) typing.remove();

                let data = null;
                try {
                    data = JSON.parse(rawText);
                } catch (e) {
                    console.warn('Response parsing error:', e, rawText);
                }

                if (data && data.response) {
                    addMessage('bot', data.response);
                } else if (data && data.error) {
                    addMessage('bot', data.error);
                } else {
                    addMessage('bot', `Hi! I'm Saravana's AI assistant. I received your query about "${text}". How can I assist you with Saravana's experience, skills, or AI projects?`);
                }
            } catch (error) {
                console.error('Chat connection error:', error);
                const typing = document.getElementById(typingId);
                if (typing) typing.remove();
                addMessage('bot', `Hi! I'm Saravana's AI assistant. I am here to help you explore Saravana's machine learning skills, research, and projects!`);
            }
        };

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function addMessage(role, text) {
            const msg = document.createElement('div');
            msg.className = `message ${role}-message`;
            
            // Format line breaks
            msg.innerHTML = text.replace(/\n/g, '<br>');
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }
    }
})();
