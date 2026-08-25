const I18N = {
  en: {
    login_subtitle: 'Build apps with AI', login_google: 'Sign in with Google',
    google_not_configured: 'Google login is not configured.',
    google_config_hint: 'Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable.',
    logout: 'Logout', my_projects: 'My Projects', new_project: 'New Project',
    no_projects: 'No projects yet. Create your first one!',
    create_project: 'Create Project', project_name: 'Project Name',
    project_description: 'Description (optional)', project_type: 'Project Type',
    cancel: 'Cancel', create: 'Create', files: 'Files', loading: 'Loading...',
    select_file: 'Select a file to edit', ai_chat: 'AI Chat',
    chat_empty: 'Ask AI to build or modify your project',
    terminal: 'Terminal', preview: 'Preview', run: 'Run', stop: 'Stop',
    preview_empty: 'Run your project to see preview',
    file_saved: 'File saved', file_deleted: 'File deleted',
    project_created: 'Project created', error: 'Error',
    ai_not_configured: 'AI is not configured', workspace_starting: 'Starting workspace...',
    workspace_stopping: 'Stopping workspace...', workspace_running: 'Running',
    workspace_stopped: 'Stopped', workspace_error: 'Error',
  },
  ar: {
    login_subtitle: 'ابنِ تطبيقاتك بالذكاء الاصطناعي', login_google: 'تسجيل الدخول عبر Google',
    google_not_configured: 'تسجيل الدخول عبر Google غير مُهيأ.',
    google_config_hint: 'اضبط GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET لتفعيله.',
    logout: 'تسجيل الخروج', my_projects: 'مشاريعي', new_project: 'مشروع جديد',
    no_projects: 'لا توجد مشاريع بعد. أنشئ أول مشروع!',
    create_project: 'إنشاء مشروع', project_name: 'اسم المشروع',
    project_description: 'الوصف (اختياري)', project_type: 'نوع المشروع',
    cancel: 'إلغاء', create: 'إنشاء', files: 'الملفات', loading: 'جارٍ التحميل...',
    select_file: 'اختر ملفاً للتعديل', ai_chat: 'دردشة الذكاء الاصطناعي',
    chat_empty: 'اطلب من الذكاء الاصطناعي بناء أو تعديل مشروعك',
    terminal: 'الطرفية', preview: 'معاينة', run: 'تشغيل', stop: 'إيقاف',
    preview_empty: 'شغّل مشروعك لرؤية المعاينة',
    file_saved: 'تم حفظ الملف', file_deleted: 'تم حذف الملف',
    project_created: 'تم إنشاء المشروع', error: 'خطأ',
    ai_not_configured: 'الذكاء الاصطناعي غير مُهيأ', workspace_starting: 'جارٍ تشغيل المساحة...',
    workspace_stopping: 'جارٍ إيقاف المساحة...', workspace_running: 'يعمل',
    workspace_stopped: 'متوقف', workspace_error: 'خطأ',
  }
};

function getCurrentLang() {
  return document.documentElement.lang || 'en';
}

function t(key) {
  const lang = getCurrentLang();
  return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t(key);
  });
}

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  fetch('/api/users/me/theme/' + next, { method: 'POST' }).catch(() => {});
  if (window.editor) {
    window.editor.setOption('theme', next === 'dark' ? 'material-darker' : 'default');
  }
}

function toggleLanguage() {
  const html = document.documentElement;
  const current = html.getAttribute('lang');
  const next = current === 'en' ? 'ar' : 'en';
  html.setAttribute('lang', next);
  html.setAttribute('dir', next === 'ar' ? 'rtl' : 'ltr');
  localStorage.setItem('language', next);
  fetch('/api/users/me/language/' + next, { method: 'POST' }).catch(() => {});
  applyTranslations();
  const label = document.getElementById('lang-label');
  if (label) label.textContent = next.toUpperCase();
}

function showNotification(message, type = 'info') {
  const notif = document.createElement('div');
  notif.className = 'notification ' + type;
  notif.textContent = message;
  document.body.appendChild(notif);
  setTimeout(() => notif.remove(), 3000);
}

function showNewProjectModal() {
  document.getElementById('new-project-modal').classList.remove('hidden');
}

function hideNewProjectModal() {
  document.getElementById('new-project-modal').classList.add('hidden');
}

async function createProject(e) {
  e.preventDefault();
  const form = e.target;
  const data = {
    name: form.name.value,
    description: form.description.value,
    project_type: form.project_type.value,
  };
  try {
    const resp = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (resp.ok) {
      const project = await resp.json();
      window.location.href = '/workspace/' + project.id;
    } else {
      const err = await resp.json();
      showNotification(err.error || t('error'), 'error');
    }
  } catch (err) {
    showNotification(err.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
