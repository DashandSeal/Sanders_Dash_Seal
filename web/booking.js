'use strict';
const $ = id => document.getElementById(id);
const serviceNames = {MOBILE_NOTARY: 'Mobile notary', AUTHORIZED_DOCUMENT_SERVICE: 'Document support'};
const form = $('booking-form');
let requestId = crypto.randomUUID();
form.addEventListener('input', () => { requestId = crypto.randomUUID(); });
$('timezone').textContent = 'Times shown in ' + Intl.DateTimeFormat().resolvedOptions().timeZone;
const money = cents => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(cents / 100);

async function api(path, data) {
  const response = await fetch(path, {credentials: 'same-origin', cache: 'no-store',
    headers: data === undefined ? {} : {'Content-Type': 'application/json'},
    method: data === undefined ? 'GET' : 'POST',
    body: data === undefined ? undefined : JSON.stringify(data)});
  if (!response.ok) {
    const error = new Error('Request unavailable'); error.status = response.status; throw error;
  }
  return response.json();
}
function node(tag, text, className) {
  const element = document.createElement(tag); element.textContent = text;
  if (className) element.className = className;
  return element;
}
function unavailable(error, target) {
  target.textContent = error.status === 401 ? 'Please sign in to continue.' :
    error.status === 409 ? 'This quote is not currently available for payment. Please contact us.' :
    'Online requests are temporarily unavailable. Please call 414-502-3325 for assistance.';
  if (error.status === 401) { $('signin').hidden = false; $('booking-fields').disabled = true; }
}
async function loadRequests() {
  const data = await api('/api/appointments');
  $('requests').replaceChildren();
  if (!data.appointments.length) {
    $('requests').append(node('p', 'No requests yet. Start with your preferred service and time.', 'empty'));
  }
  for (const record of data.appointments) {
    const button = node('button', '', 'request-item'); button.type = 'button';
    button.append(node('strong', serviceNames[record.service] || 'Service request'),
      node('span', new Date(record.requested_start).toLocaleString() + ' · ' + record.jurisdiction),
      node('span', 'Awaiting human review'));
    button.addEventListener('click', () => loadDetails(record.case_id).catch(e => unavailable(e, $('notice'))));
    $('requests').append(button);
  }
}
async function loadDetails(caseId) {
  const data = await api('/api/appointments/' + encodeURIComponent(caseId));
  const panel = $('details'); panel.hidden = false; panel.replaceChildren();
  panel.append(node('h3', 'Request details'), node('p', 'Reference: ' + data.appointment.case_id),
    node('p', 'Preferred time: ' + new Date(data.appointment.requested_start).toLocaleString()),
    node('p', 'Area: ' + data.appointment.meeting_area),
    node('p', 'Your requested time is awaiting confirmation.'));
  if (!data.quote) { panel.append(node('p', 'Your itemized quote will appear here after review.')); return; }
  panel.append(node('h3', 'Your quote'));
  for (const [label, cents] of Object.entries(data.quote.items)) {
    const row = node('div', '', 'quote-row'); row.append(node('span', label), node('strong', money(cents))); panel.append(row);
  }
  panel.append(node('p', 'Total: ' + money(data.quote.total_cents)),
    node('p', 'Quote valid until ' + new Date(data.quote.expires_at * 1000).toLocaleString()));
  if (data.payment === 'PAID') { panel.append(node('p', 'Payment received. Appointment confirmation is separate.')); return; }
  if (data.quote.expired) { panel.append(node('p', 'This quote has expired. Please contact us for an updated quote.')); return; }
  const label = node('label', '', 'check'), accept = document.createElement('input');
  accept.type = 'checkbox';
  label.append(accept, node('span', 'I accept this itemized quote and want to continue to secure payment.'));
  const pay = node('button', 'Continue to secure payment ↗', 'primary'); pay.type = 'button'; pay.disabled = true;
  accept.addEventListener('change', () => { pay.disabled = !accept.checked; });
  const message = node('p', ''); message.setAttribute('role', 'status');
  pay.addEventListener('click', async () => {
    pay.disabled = true;
    try {
      const result = await api('/api/appointments/' + encodeURIComponent(caseId) + '/checkout',
        {quote_id: data.quote.quote_id, accept_quote: accept.checked});
      const url = new URL(result.url);
      if (url.protocol !== 'https:' || url.host !== 'checkout.stripe.com') throw new Error('Invalid payment destination');
      window.location.assign(url.href);
    } catch (error) { unavailable(error, message); pay.disabled = !accept.checked; }
  });
  panel.append(label, pay, message);
}
form.addEventListener('submit', async event => {
  event.preventDefault(); if (!form.reportValidity()) return;
  $('submit').disabled = true; $('form-message').textContent = 'Sending your request…';
  try {
    const date = new Date($('requested-start').value);
    if (!Number.isFinite(date.getTime())) throw new Error('Invalid time');
    const data = await api('/api/appointments', {request_id: requestId,
      jurisdiction: $('jurisdiction').value, service: $('service').value,
      requested_start: date.toISOString(), meeting_area: $('meeting-area').value,
      consent: $('consent').checked});
    $('form-message').textContent = 'Request received. Your time is awaiting confirmation. Reference: ' + data.appointment.case_id;
    requestId = crypto.randomUUID(); form.reset();
    await loadRequests(); await loadDetails(data.appointment.case_id);
  } catch (error) {
    if (error.status === 400) $('form-message').textContent = 'Check your requested time and details, then try again.';
    else unavailable(error, $('form-message'));
  } finally { $('submit').disabled = false; }
});
(async () => {
  try { await api('/api/session'); $('notice').textContent = ''; $('booking-fields').disabled = false; await loadRequests(); }
  catch (error) { unavailable(error, $('notice')); }
})();
