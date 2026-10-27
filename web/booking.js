/* =========================================================================
 * Module: web/booking.js
 * Architectural Layer: Touch-Screen Responsive Mobile App Control Core
 * Property of: Sanders Legal Helpers LLC | Developed by: Roosevelt Sanders
 * Custom Platform: Sanders Dash & Seal
 * ========================================================================= */

"use strict";

const $ = id => document.getElementById(id);
const serviceNames = { MOBILE_NOTARY: 'Mobile Notary', AUTHORIZED_DOCUMENT_SERVICE: 'Document Support', RON: 'Remote Online Notarization' };
const form = $('booking-form');
let requestId = crypto.randomUUID();

form.addEventListener('input', () => { if (!requestId) requestId = crypto.randomUUID(); });
$('timezone').textContent = "Times shown in " + Intl.DateTimeFormat().resolvedOptions().timeZone;
const money = cents => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);

// Hybrid App API Request Wrapper with Timeout Protection
async function api(path, data) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s mobile timeout gate

    try {
        const response = await fetch(path, {
            credentials: 'same-origin',
            cache: 'no-store',
            headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
            method: data === undefined ? 'GET' : 'POST',
            body: data === undefined ? undefined : JSON.stringify(data),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (!response.ok) {
            const error = new Error('Network response out of bounds');
            error.status = response.status;
            throw error;
        }
        return response.json();
    } catch (err) {
        clearTimeout(timeoutId);
        throw err;
    }
}

function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

function functionUnavailable(error, target) {
    target.textContent = error.status === 401 ? 'Please sign in to continue.' : 'Online requests are temporarily unavailable. Please call 414-502-3325.';
    if (error.status === 401) {
        $('signin').hidden = false;
        $('booking-fields').disabled = true;
    }
}

// Enterprise Touch & Click Unified Event Binder
function bindTouchEvent(element, callback) {
    if (!element) return;
    let touchMoved = false;

    // Fast-track mobile touch gestures natively without 300ms lag loops
    element.addEventListener('touchstart', () => { touchMoved = false; }, { passive: true });
    element.addEventListener('touchmove', () => { touchMoved = true; }, { passive: true });
    element.addEventListener('touchend', (e) => {
        if (!touchMoved) {
            e.preventDefault();
            callback(e);
        }
    });
    // Fallback alignment for pointer devices and desktop clicks
    element.addEventListener('click', (e) => {
        callback(e);
    });
}

async function functionLoadRequests() {
    try {
        const data = await api('/api/appointments');
        $('requests').replaceChildren();
        if (!data.appointments || data.appointments.length === 0) {
            $('requests').append(node('p', 'sds-empty-msg', 'No requests yet. Start with your preferred service and time.'));
            return;
        }

        for (const record of data.appointments) {
            const button = node('button', 'request-item sds-action-card', '');
            button.type = 'button';
            button.setAttribute('role', 'button');
            button.append(node('strong', '', serviceNames[record.service] || 'Service Request'));
            button.append(node('span', 'sds-date-string', new Date(record.requested_start).toLocaleString()));
            button.append(node('span', 'sds-status-badge', 'Awaiting Human Review'));
            
            // FIX: Enforce touch gesture bindings for fast loading responses
            bindTouchEvent(button, () => {
                loadDetails(record.case_id).catch(e => functionUnavailable(e, $('notice')));
            });
            $('requests').append(button);
        }
    } catch (e) {
        functionUnavailable(e, $('notice'));
    }
}

async function loadDetails(caseId) {
    const data = await api('/api/appointments/' + encodeURIComponent(caseId));
    const panel = $('details');
    panel.hidden = false;
    panel.replaceChildren();

    panel.append(node('h3', 'sds-subheading', 'Request Details'));
    panel.append(node('p', '', 'Reference: ' + data.appointment.case_id));
    panel.append(node('p', '', 'Preferred Time: ' + new Date(data.appointment.requested_start).toLocaleString()));
    panel.append(node('p', '', 'Area: ' + data.appointment.meeting_area));

    if (!data.quote) {
        panel.append(node('p', 'sds-notice-highlight', 'Your itemized quote will appear here after manual human review.'));
        return;
    }

    panel.append(node('h3', 'sds-subheading', 'Your Quote'));
    for (const [label, cents] of Object.entries(data.quote.items)) {
        const row = node('div', 'quote-row');
        row.append(node('span', '', label));
        row.append(node('strong', '', money(cents)));
        panel.append(row);
    }

    panel.append(node('p', 'sds-total-row', 'Total: ' + money(data.quote.total_cents)));
    
    if (data.payment === 'PAID') {
        panel.append(node('p', 'sds-success-badge', 'Payment received. Appointment confirmation is separate.'));
        return;
    }

    if (data.quote.expired) {
        panel.append(node('p', 'sds-error-badge', 'This quote has expired. Please contact us for an updated quote.'));
        return;
    }

    const label = node('label', 'sds-checkbox-label', '');
    const accept = document.createElement('input');
    accept.type = 'checkbox';
    accept.id = 'accept-quote-check';
    label.append(accept);
    label.append(node('span', '', 'I accept this itemized quote and want to continue to secure payment.'));
    panel.append(label);

    const pay = node('button', 'sds-button-primary', 'Continue to secure payment');
    pay.type = 'button';
    pay.disabled = true;
    panel.append(pay);

    accept.addEventListener('change', () => { pay.disabled = !accept.checked; });

    // FIX: Optimized fast touch-event handling on payment redirects
    bindTouchEvent(pay, async () => {
        pay.disabled = true;
        try {
            const result = await api('/api/appointments/' + encodeURIComponent(caseId) + '/checkout', {
                quote_id: data.quote.quote_id,
                accept_quote: accept.checked
            });
            const url = new URL(result.url);
            if (url.protocol !== 'https:' || !url.host.endswith('.stripe.com')) {
                throw new Error('Invalid payment destination address');
            }
            window.location.assign(url.href);
        } catch (error) {
            functionUnavailable(error, $('notice'));
            pay.disabled = !accept.checked;
        }
    });
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    $('submit').disabled = true;
    $('form-message').textContent = 'Sending your request...';

    try {
        const date = new Date($('requested-start').value);
        if (isNaN(date.getTime())) throw new Error('Invalid scheduled time window configuration');

        const data = await api('/api/appointments', {
            request_id: requestId,
            jurisdiction: $('jurisdiction').value,
            service: $('service').value,
            requested_start: date.toISOString(),
            meeting_area: $('meeting-area').value,
            consent: $('consent').checked
        });

        $('form-message').textContent = 'Request received. Your time is awaiting confirmation. Reference: ' + data.appointment.case_id;
        requestId = crypto.randomUUID();
        form.reset();
        await functionLoadRequests();
    } catch (error) {
        if (error.status === 401) {
            $('form-message').textContent = 'Check your requested time and details, then try again.';
        } else {
            $('form-message').textContent = error.message || 'Submission failed. Please check network connection.';
        }
    } finally {
        $('submit').disabled = false;
    }
});

// Cold-Start Device Ingress Initialization
(async () => {
    try {
        await api('/api/session');
        $('notice').textContent = '';
        $('booking-fields').disabled = false;
        await functionLoadRequests();
    } catch (error) {
        functionUnavailable(error, $('notice'));
    }
})();
