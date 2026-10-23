'use strict';
const queue = document.getElementById('queue'), notice = document.getElementById('notice');
function el(tag, text) { const n = document.createElement(tag); n.textContent = text; return n; }
function cents(value) {
  if (!/^\d{1,6}(\.\d{1,2})?$/.test(value)) throw new Error('Enter a valid dollar amount.');
  const [whole, fraction = ''] = value.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}
async function load() {
  const response = await fetch('/api/operator/appointments', {credentials: 'same-origin', cache: 'no-store'});
  if (!response.ok) {
    notice.textContent = response.status === 401 ? 'Sign in to your authorized operator account to continue.' :
      response.status === 403 ? 'This account does not have operator access.' : 'Appointment review is currently unavailable.';
    if (response.status === 401) { const link = el('a', ' Sign in →'); link.href = '/auth/login'; notice.append(link); }
    return;
  }
  const data = await response.json(); notice.textContent = data.appointments.length ? '' : 'No appointment requests yet.';
  for (const record of data.appointments) {
    const card = el('section', ''); card.className = 'card';
    card.append(el('h2', record.service === 'MOBILE_NOTARY' ? 'Mobile notary request' : 'Document-support request'),
      el('p', record.case_id), el('p', record.jurisdiction + ' · ' + record.meeting_area),
      el('p', 'Preferred: ' + new Date(record.requested_start).toLocaleString()));
    const form = el('form', ''), amounts = {};
    for (const name of ['Notarial acts', 'Travel', 'Document support']) {
      const label = el('label', name + ' (USD)'), input = document.createElement('input');
      input.type = 'number'; input.min = '0'; input.max = '999999.99'; input.step = '0.01'; input.required = true;
      label.append(input); form.append(label); amounts[name] = input;
    }
    const expiresLabel = el('label', 'Quote valid until (your local time)'), expires = document.createElement('input');
    expires.type = 'datetime-local'; expires.required = true; expiresLabel.append(expires); form.append(expiresLabel);
    const attestation = el('label', ''), check = document.createElement('input');
    attestation.className = 'check'; check.type = 'checkbox'; check.required = true;
    attestation.append(check, el('span', 'I have reviewed these fees and their applicability to this service.'));
    const button = el('button', 'Approve itemized quote'); button.type = 'submit'; button.className = 'primary';
    const status = el('p', ''); status.setAttribute('role', 'status'); form.append(attestation, button, status);
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (!form.reportValidity()) return; button.disabled = true;
      try {
        const items = Object.fromEntries(Object.entries(amounts).map(([name, input]) => [name, cents(input.value)]));
        const result = await fetch('/api/operator/appointments/' + encodeURIComponent(record.case_id) + '/quote', {
          method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({items, expires_at: Math.floor(new Date(expires.value).getTime() / 1000)})});
        if (!result.ok) throw new Error('Quote was not approved. Check fee eligibility, expiry and whether a quote already exists.');
        status.textContent = 'Quote approved. It is now available in the customer’s request details.';
      } catch (error) { status.textContent = error.message; button.disabled = false; }
    });
    card.append(form, providerPanel(record)); queue.append(card);
  }
}
load().catch(() => { notice.textContent = 'Appointment review is currently unavailable.'; });

function providerPanel(record) {
  const panel = el('details', ''); panel.append(el('summary', 'Signing and RON requests'));
  panel.append(el('p', 'Create a SignWell signing request or a BlueNotary RON session using your provider templates.'));
  const history = el('p', 'Loading existing provider requests…'); panel.append(history);
  const endpoint = '/api/operator/appointments/' + encodeURIComponent(record.case_id) + '/providers';
  const updateHistory = async () => {
    const response = await fetch(endpoint, {credentials: 'same-origin', cache: 'no-store'});
    if (!response.ok) { history.textContent = 'Provider request history is unavailable.'; return; }
    const data = await response.json();
    history.textContent = data.requests.length ? data.requests.map(r =>
      r.provider + ': ' + r.state + ' · ' + (r.resource_id || r.request_id)).join(' | ') : 'No provider requests yet.';
  };
  updateHistory().catch(() => { history.textContent = 'Provider request history is unavailable.'; });
  const form = el('form', ''), fields = {};
  const providerLabel = el('label', 'Provider'), provider = document.createElement('select');
  for (const [value, label] of [['signwell', 'SignWell signing'], ['bluenotary', 'BlueNotary RON']]) {
    const option = el('option', label); option.value = value; provider.append(option);
  }
  providerLabel.append(provider); form.append(providerLabel);
  for (const [key, label, type] of [['template', 'Provider template ID', 'text'],
      ['first', 'Signer first name', 'text'], ['last', 'Signer last name', 'text'],
      ['email', 'Signer email', 'email'], ['placeholder', 'SignWell template placeholder name', 'text'],
      ['notary', 'BlueNotary notary account email', 'email']]) {
    const container = el('label', label), input = document.createElement('input');
    input.type = type; input.required = true; input.maxLength = key === 'email' || key === 'notary' ? 254 : 128;
    container.append(input); form.append(container); fields[key] = {input, container};
  }
  const changeProvider = () => {
    for (const key of ['placeholder', 'notary']) {
      const active = key === (provider.value === 'signwell' ? 'placeholder' : 'notary');
      fields[key].container.hidden = !active; fields[key].input.required = active;
    }
  };
  provider.addEventListener('change', changeProvider); changeProvider();
  const submit = el('button', 'Create provider request'), status = el('p', '');
  submit.type = 'submit'; submit.className = 'primary'; status.setAttribute('role', 'status');
  form.append(submit, status); panel.append(form);
  const requestId = crypto.randomUUID();
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!form.reportValidity()) return; submit.disabled = true;
    const value = key => fields[key].input.value.trim();
    let payload = {request_id: requestId};
    if (provider.value === 'signwell') {
      Object.assign(payload, {template_id: value('template'), name: 'Sanders Dash & Seal ' + record.case_id,
        recipients: [{id: '1', placeholder_name: value('placeholder'),
          name: value('first') + ' ' + value('last'), email: value('email')}]});
    } else {
      Object.assign(payload, {document_templates: [value('template')],
        all_signers: [{first_name: value('first'), last_name: value('last'), email: value('email')}],
        session_notary_email: value('notary'), notarization_timing_type: 'notarize_now'});
    }
    try {
      const response = await fetch(endpoint + '/' + provider.value, {method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
      if (!response.ok) {
        status.textContent = response.status === 400 ? 'Check the template and recipient fields.' :
          'Request was not confirmed. Review the request history and provider account before submitting again.';
        // An ambiguous provider outcome must not silently create another session.
        if (response.status === 400) submit.disabled = false;
      } else {
        const result = await response.json();
        status.textContent = 'Provider accepted request: ' + result.resource_id + '. Signing and notarial completion remain separate.';
      }
      await updateHistory();
    } catch (_) {
      status.textContent = 'Connection interrupted. Check request history and your provider account before submitting again.';
    }
  });
  return panel;
}
