function getProjectId() {
  return document.querySelector('.workspace-container')?.dataset.projectId;
}

function getSessionToken() {
  return document.cookie.match(/forge_session=([^;]+)/)?.[1] || '';
}

async function loadFileTree() {
  const projectId = getProjectId();
  if (!projectId) return;
  const treeEl = document.getElementById('file-tree');
  try {
    const resp = await fetch(`/api/projects/${projectId}/files/tree`);
    if (!resp.ok) return;
    const tree = await resp.json();
    treeEl.innerHTML = '';
    renderTreeItem(tree, treeEl, true);
  } catch (err) {
    treeEl.innerHTML = '<div class="file-tree-loading">Error loading files</div>';
  }
}

function renderTreeItem(item, parent, isRoot) {
  const el = document.createElement('div');
  el.className = 'tree-item';
  if (item.type === 'file') {
    el.innerHTML = `<span class="tree-item-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg></span><span class="tree-item-name">${item.name}</span>`;
    el.onclick = () => {
      document.querySelectorAll('.tree-item.active').forEach(t => t.classList.remove('active'));
      el.classList.add('active');
      openFile(item.path);
    };
    parent.appendChild(el);
  } else {
    let icon = isRoot
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
      : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
    el.innerHTML = `<span class="tree-item-icon">${icon}</span><span class="tree-item-name">${item.name}</span>`;
    const children = document.createElement('div');
    children.className = 'tree-children';
    children.style.display = 'block';
    el.onclick = () => {
      const isShown = children.style.display === 'block';
      children.style.display = isShown ? 'none' : 'block';
    };
    parent.appendChild(el);
    parent.appendChild(children);
    if (item.children) {
      item.children.forEach(child => renderTreeItem(child, children, false));
    }
  }
}

async function createFile() {
  const name = prompt('File name (with path, e.g. src/main.py):');
  if (!name) return;
  const projectId = getProjectId();
  try {
    const resp = await fetch(`/api/projects/${projectId}/files/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: name, content: '' }),
    });
    if (resp.ok) { loadFileTree(); showNotification('File created', 'success'); }
  } catch (err) { showNotification(err.message, 'error'); }
}

async function createFolder() {
  const name = prompt('Folder name:');
  if (!name) return;
  const projectId = getProjectId();
  try {
    const resp = await fetch(`/api/projects/${projectId}/files/mkdir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: name }),
    });
    if (resp.ok) { loadFileTree(); showNotification('Folder created', 'success'); }
  } catch (err) { showNotification(err.message, 'error'); }
}

function refreshFileTree() { loadFileTree(); }

let ws = null;

async function runWorkspace() {
  const projectId = getProjectId();
  const btnRun = document.getElementById('btn-run');
  const btnStop = document.getElementById('btn-stop');
  btnRun.classList.add('hidden');
  btnStop.classList.remove('hidden');
  updateStatus('building');
  try {
    const resp = await fetch(`/api/projects/${projectId}/start`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      updateStatus('running');
      togglePanel('terminal');
    } else {
      updateStatus('error');
      showNotification(data.error || 'Failed to start', 'error');
      btnRun.classList.remove('hidden');
      btnStop.classList.add('hidden');
    }
  } catch (err) {
    updateStatus('error');
    showNotification(err.message, 'error');
    btnRun.classList.remove('hidden');
    btnStop.classList.add('hidden');
  }
}

async function stopWorkspace() {
  const projectId = getProjectId();
  const btnRun = document.getElementById('btn-run');
  const btnStop = document.getElementById('btn-stop');
  try {
    await fetch(`/api/projects/${projectId}/stop`, { method: 'POST' });
    updateStatus('stopped');
    btnRun.classList.remove('hidden');
    btnStop.classList.add('hidden');
  } catch (err) { showNotification(err.message, 'error'); }
}

function updateStatus(status) {
  const dot = document.getElementById('workspace-status-dot');
  const text = document.getElementById('workspace-status-text');
  if (dot) dot.className = 'status-dot status-' + status;
  if (text) text.textContent = t('workspace_' + status) || status;
}

function togglePanel(panel) {
  const el = document.getElementById(panel + '-panel');
  if (el) el.classList.toggle('hidden');
}

function refreshPreview() {
  const iframe = document.querySelector('.preview-iframe');
  if (iframe) iframe.src = iframe.src;
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('.workspace-container')) {
    initEditor();
    loadFileTree();
    initResizers();
    checkServices();
  }
});

async function checkServices() {
  try {
    const resp = await fetch('/api/services/status');
    const data = await resp.json();
    const aiStatus = document.getElementById('ai-status');
    if (aiStatus) {
      if (data.ai.available) {
        aiStatus.textContent = 'AI';
        aiStatus.className = 'chat-status configured';
      } else {
        aiStatus.textContent = t('ai_not_configured');
        aiStatus.className = 'chat-status not-configured';
      }
    }
  } catch (err) { /* ignore */ }
}

function initResizers() {
  const resizers = document.querySelectorAll('.resizer');
  resizers.forEach(r => {
    let isDragging = false;
    let startX, startWidth;
    r.addEventListener('mousedown', (e) => {
      isDragging = true;
      startX = e.clientX;
      r.classList.add('dragging');
      const target = r.previousElementSibling;
      if (target) startWidth = target.offsetWidth;
      document.body.style.cursor = r.classList.contains('resizer-horizontal') ? 'col-resize' : 'row-resize';
      e.preventDefault();
    });
    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const target = r.previousElementSibling;
      if (!target) return;
      const dx = e.clientX - startX;
      const newWidth = Math.max(100, startWidth + dx);
      target.style.width = newWidth + 'px';
    });
    document.addEventListener('mouseup', () => {
      if (isDragging) { isDragging = false; r.classList.remove('dragging'); document.body.style.cursor = ''; }
    });
  });
}
