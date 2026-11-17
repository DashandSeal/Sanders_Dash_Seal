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
    card.append(form); queue.append(card);
  }
}
load().catch(() => { notice.textContent = 'Appointment review is currently unavailable.'; });
