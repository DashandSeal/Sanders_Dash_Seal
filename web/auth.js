'use strict';
const el = id => document.getElementById(id);
const mode = location.pathname.split('/').pop();
const modes = {login: ['Sign in', 'Sign in to request an appointment and follow its progress.'],
  register: ['Create an account', 'Choose an account name and a passphrase of at least 15 characters.'],
  setup: ['Set up owner access', 'Use your private owner setup secret to establish operator access.'],
  logout: ['Sign out', 'Sign out of this browser session and its access tokens.']};
const selected = modes[mode] || modes.login;
el('auth-title').textContent = selected[0];
el('auth-description').textContent = selected[1];
el('account-submit').textContent = selected[0];
if (mode === 'register' || mode === 'setup') el('password').autocomplete = 'new-password';
if (mode === 'setup') { el('setup-field').hidden = false; el('setup-token').required = true; }
if (mode !== 'login') { el('auth-alternative').href = '/auth/login'; el('auth-alternative').textContent = 'Back to sign in'; }
if (mode === 'logout') {
  el('account-fields').hidden = true;
  el('username').required = false; el('password').required = false;
}
async function post(path, body) {
  const response = await fetch(path, {method: 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  if (!response.ok) throw new Error(response.status === 429 ? 'Please wait a minute and try again.' :
    'Unable to complete this request. Check your details and try again.');
  return response.json();
}
el('account-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!event.target.reportValidity()) return;
  el('account-submit').disabled = true; el('auth-message').textContent = 'Please wait…';
  try {
    const body = mode === 'logout' ? {} : {username: el('username').value, password: el('password').value};
    if (mode === 'setup') body.setup_token = el('setup-token').value;
    await post('/auth/' + (modes[mode] ? mode : 'login'), body);
    if (mode === 'register' || mode === 'setup') await post('/auth/login', {username: body.username, password: body.password});
    el('password').value = ''; el('setup-token').value = '';
    location.assign(mode === 'setup' ? '/operator' : mode === 'logout' ? '/' : '/appointments');
  } catch (error) { el('auth-message').textContent = error.message; }
  finally { el('account-submit').disabled = false; }
});
