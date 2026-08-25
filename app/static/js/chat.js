let chatWs = null;
let chatHistory = [];

function initChatWebSocket() {
  const projectId = getProjectId();
  const token = getSessionToken();
  if (!projectId || !token) return;
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  chatWs = new WebSocket(`${protocol}://${location.host}/ws/ai/${projectId}?token=${token}`);
  chatWs.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    handleChatMessage(msg);
  };
  chatWs.onclose = () => {
    setTimeout(() => { if (document.querySelector('.workspace-container')) initChatWebSocket(); }, 3000);
  };
}

function handleChatMessage(msg) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  if (msg.type === 'message') {
    addChatMessage('assistant', msg.data);
  } else if (msg.type === 'tool_call') {
    addChatMessage('tool', `Tool: ${msg.data.name}(${JSON.stringify(msg.data.arguments).slice(0, 100)})`);
  } else if (msg.type === 'tool_result') {
    addChatMessage('tool', `Result: ${msg.data.result.slice(0, 200)}`);
  } else if (msg.type === 'error') {
    addChatMessage('error', msg.data);
  }
}

function addChatMessage(role, content) {
  const messages = document.getElementById('chat-messages');
  const empty = messages.querySelector('.chat-empty');
  if (empty) empty.remove();
  const msg = document.createElement('div');
  msg.className = 'chat-msg ' + role;
  msg.textContent = content;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}

function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  addChatMessage('user', message);
  chatHistory.push({ role: 'user', content: message });
  input.value = '';
  if (chatWs && chatWs.readyState === WebSocket.OPEN) {
    chatWs.send(JSON.stringify({ type: 'chat', message, history: chatHistory }));
    const typing = document.createElement('div');
    typing.className = 'chat-msg assistant typing';
    typing.id = 'typing-indicator';
    document.getElementById('chat-messages').appendChild(typing);
    setTimeout(() => document.getElementById('typing-indicator')?.remove(), 5000);
  } else {
    fetch(`/api/projects/${getProjectId()}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history: chatHistory }),
    })
    .then(r => r.json())
    .then(data => {
      if (data.results) {
        data.results.forEach(chunk => {
          if (chunk.type === 'message') addChatMessage('assistant', chunk.data);
          else if (chunk.type === 'error') addChatMessage('error', chunk.data);
        });
      }
    })
    .catch(err => addChatMessage('error', err.message));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('.workspace-container')) {
    initChatWebSocket();
    const input = document.getElementById('chat-input');
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
      });
    }
  }
});
