let editor = null;
let openTabs = {};
let activeTab = null;
const MODE_MAP = {
  '.py': 'python', '.js': 'javascript', '.ts': 'javascript',
  '.html': 'htmlmixed', '.css': 'css', '.json': 'application/json',
  '.md': 'markdown', '.yml': 'yaml', '.yaml': 'yaml',
  '.dart': 'dart', '.sql': 'sql', '.sh': 'shell', '.txt': 'text',
  '.toml': 'toml', '.cfg': 'text', '.ini': 'text', '.env': 'text',
};

function getModeForFile(filename) {
  const ext = '.' + filename.split('.').pop().toLowerCase();
  return MODE_MAP[ext] || 'text';
}

function initEditor() {
  const textarea = document.getElementById('code-editor');
  if (!textarea) return;
  textarea.style.display = 'block';
  editor = CodeMirror.fromTextArea(textarea, {
    lineNumbers: true,
    mode: 'python',
    theme: document.documentElement.getAttribute('data-theme') === 'light' ? 'default' : 'material-darker',
    indentUnit: 4,
    tabSize: 4,
    lineWrapping: false,
    matchBrackets: true,
    autoCloseBrackets: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
    extraKeys: {
      'Ctrl-S': saveCurrentFile,
      'Cmd-S': saveCurrentFile,
      'Ctrl-F': 'find',
      'Cmd-F': 'find',
      'Ctrl-Space': 'autocomplete',
    },
  });
  window.editor = editor;
}

async function openFile(path) {
  if (openTabs[path]) {
    switchTab(path);
    return;
  }
  const projectId = getProjectId();
  if (!projectId) return;
  try {
    const resp = await fetch(`/api/projects/${projectId}/files/read?path=${encodeURIComponent(path)}`);
    if (!resp.ok) { showNotification('Failed to read file', 'error'); return; }
    const data = await resp.json();
    openTabs[path] = { content: data.content, dirty: false };
    addTab(path);
    switchTab(path);
  } catch (err) {
    showNotification(err.message, 'error');
  }
}

function addTab(path) {
  const tabsList = document.getElementById('editor-tabs-list');
  const tab = document.createElement('div');
  tab.className = 'editor-tab';
  tab.dataset.path = path;
  const name = path.split('/').pop();
  tab.innerHTML = `<span>${name}</span><span class="editor-tab-close" onclick="closeTab('${path}', event)">&times;</span>`;
  tab.onclick = (e) => {
    if (e.target.classList.contains('editor-tab-close')) return;
    switchTab(path);
  };
  tabsList.appendChild(tab);
}

function switchTab(path) {
  if (!openTabs[path]) return;
  activeTab = path;
  document.querySelectorAll('.editor-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.path === path);
  });
  editor.setValue(openTabs[path].content);
  editor.setOption('mode', getModeForFile(path));
  document.querySelector('.editor-placeholder')?.classList.add('hidden');
  document.querySelector('.CodeMirror')?.classList.remove('hidden');
}

function closeTab(path, event) {
  if (event) event.stopPropagation();
  delete openTabs[path];
  document.querySelector(`.editor-tab[data-path="${path}"]`)?.remove();
  if (activeTab === path) {
    activeTab = null;
    const remaining = Object.keys(openTabs);
    if (remaining.length > 0) {
      switchTab(remaining[0]);
    } else {
      editor.setValue('');
      document.querySelector('.editor-placeholder')?.classList.remove('hidden');
    }
  }
}

async function saveCurrentFile() {
  if (!activeTab) return;
  const projectId = getProjectId();
  openTabs[activeTab].content = editor.getValue();
  try {
    const resp = await fetch(`/api/projects/${projectId}/files/write`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: activeTab, content: editor.getValue() }),
    });
    if (resp.ok) {
      showNotification(t('file_saved'), 'success');
    } else {
      showNotification('Save failed', 'error');
    }
  } catch (err) {
    showNotification(err.message, 'error');
  }
}

function getProjectId() {
  return document.querySelector('.workspace-container')?.dataset.projectId;
}
