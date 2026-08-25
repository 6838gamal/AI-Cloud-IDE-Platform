let terminalWs = null;

function initTerminalWebSocket() {
  const projectId = getProjectId();
  const token = getSessionToken();
  if (!projectId || !token) return;
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  terminalWs = new WebSocket(`${protocol}://${location.host}/ws/terminal/${projectId}?token=${token}`);
  terminalWs.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'stdout' || msg.type === 'stderr') {
      appendTerminalOutput(msg.data);
    } else if (msg.type === 'exit') {
      appendTerminalOutput(`[exit code: ${msg.code}]\n`);
    } else if (msg.type === 'error') {
      appendTerminalOutput(`Error: ${msg.data}\n`);
    }
  };
  terminalWs.onclose = () => {
    setTimeout(() => { if (document.querySelector('.workspace-container')) initTerminalWebSocket(); }, 3000);
  };
}

function appendTerminalOutput(text) {
  const output = document.getElementById('terminal-output');
  if (!output) return;
  output.textContent += text;
  const body = document.getElementById('terminal-body');
  if (body) body.scrollTop = body.scrollHeight;
}

function clearTerminal() {
  const output = document.getElementById('terminal-output');
  if (output) output.textContent = '';
}

function sendTerminalCommand(cmd) {
  if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
    terminalWs.send(JSON.stringify({ type: 'command', cmd }));
  } else {
    appendTerminalOutput('Terminal not connected. Start the workspace first.\n');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('.workspace-container')) {
    initTerminalWebSocket();
    const input = document.getElementById('terminal-input');
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const cmd = input.value;
          appendTerminalOutput(`$ ${cmd}\n`);
          sendTerminalCommand(cmd);
          input.value = '';
        }
      });
    }
  }
});
