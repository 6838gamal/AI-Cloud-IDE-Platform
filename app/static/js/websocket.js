function getSessionToken() {
  return document.cookie.match(/forge_session=([^;]+)/)?.[1] || '';
}

function getProjectId() {
  return document.querySelector('.workspace-container')?.dataset.projectId;
}
