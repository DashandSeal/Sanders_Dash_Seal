/* =========================================================================
 * Module: web/operator.js
 * Architectural Layer: Touch-Responsive Notary Operator Dashboard Core
 * Property of: Sanders Legal Helpers LLC | Developed by: Roosevelt Sanders
 * Description: Manages live case reviews, itemized price quote issuance,
 *              and secure, synchronized provider workspace connections.
 * ========================================================================= */

"use strict";

const el = id => document.getElementById(id);
const queueNode = el('queue');
const noticeNode = el('notice');

function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

// Mobile-optimized touch and tap gesture binder
function bindOperatorTouch(element, callback) {
    if (!element) return;
    let touchMoved = false;
    element.addEventListener('touchstart', () => { touchMoved = false; }, { passive: true });
    element.addEventListener('touchmove', () => { touchMoved = true; }, { passive: true });
    element.addEventListener('touchend', (e) => {
        if (!touchMoved) {
            e.preventDefault();
            callback(e);
        }
    });
    element.addEventListener('click', (e) => { callback(e); });
}

async function load() {
    noticeNode.textContent = 'Fetching assigned case queue...';
    try {
        const response = await fetch('/api/operator/appointments', { credentials: 'same-origin' });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                noticeNode.replaceChildren(node('p', 'sds-error-msg', 'Operator authentication required. Please sign in.'));
                const link = node('a', 'sds-auth-link', 'Sign in ->');
                link.href = '/auth/login.html';
                noticeNode.append(link);
                return;
            }
            throw new Error('Failed to load queue telemetry');
        }

        const data = await response.json();
        noticeNode.textContent = '';
        if (queueNode) queueNode.replaceChildren();

        if (!data.appointments || data.appointments.length === 0) {
            if (queueNode) queueNode.append(node('p', 'sds-empty-msg', 'No active cases awaiting human review.'));
            return;
        }

        for (const record of data.appointments) {
            const card = node('div', 'sds-action-card case-item');
            card.append(node('h3', '', `Case: ${record.case_id}`));
            card.append(node('p', '', `Jurisdiction: ${record.jurisdiction}`));
            card.append(node('p', '', `Requested Service: ${record.service}`));
            card.append(node('p', '', `Scheduled: ${new Date(record.requested_start).toLocaleString()}`));

            const form = node('form', 'sds-quote-form');
            const items = ['Notarial Acts', 'Travel', 'Document Support'];
            const fields = {};

            items.forEach(item => {
                const row = node('div', 'sds-input-row');
                const label = node('label', '', `${item} ($): `);
                const input = node('input');
                input.type = 'number';
                input.step = '0.01';
                input.min = '0';
                input.value = '0.00';
                input.required = true;
                row.append(label, input);
                form.append(row);
                fields[item] = input;
            });

            const submitBtn = node('button', 'sds-button-primary', 'Approve Itemized Quote');
            submitBtn.type = 'submit';
            form.append(submitBtn);

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                submitBtn.disabled = true;
                
                const payload = { items: {}, expires_at: Math.floor(Date.now() / 1000) + 86400 };
                for (const [k, input] of Object.entries(fields)) {
                    payload.items[k] = math_round = Math.round(parseFloat(input.value) * 100);
                }

                try {
                    const res = await fetch(`/api/operator/appointments/${encodeURIComponent(record.case_id)}/quote`, {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (!res.ok) throw new Error('Quote submission rejected');
                    
                    card.replaceChildren(node('p', 'sds-success-msg', '🟢 Itemized Quote Active and Pushed to Client Timeline.'));
                } catch (err) {
                    submitBtn.disabled = false;
                    alert('Error finalizing quote parameters.');
                }
            });

            const manageBtn = node('button', 'sds-button-secondary', 'Open Provider Workspace');
            manageBtn.type = 'button';
            bindOperatorTouch(manageBtn, () => { providerPanel(record); });
            card.append(form, manageBtn);

            if (queueNode) queueNode.append(card);
        }
    } catch (err) {
        noticeNode.textContent = 'Operational queue currently unavailable.';
    }
}

function providerPanel(record) {
    const details = el('details');
    if (!details) return;
    details.hidden = false;
    details.replaceChildren();

    details.append(node('h3', 'sds-subheading', `RON Connection Portal: ${record.case_id}`));
    const historyLog = node('div', 'sds-history-log', 'Loading verification workflows status...');
    details.append(historyLog);

    const updateHistory = async () => {
        try {
            const res = await api_fetch = await fetch(`/api/operator/appointments/${encodeURIComponent(record.case_id)}/provider`, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('Logs unavailable');
            const logData = await res.json();
            
            // FIX: Clean, explicit join evaluation pattern to prevent object mapping array leaks
            if (logData.requests && logData.requests.length > 0) {
                historyLog.innerHTML = logData.requests.map(r => `<div>🌐 [${r.provider.toUpperCase()}] status: <strong>${r.state}</strong></div>`).join('');
            } else {
                historyLog.textContent = 'No remote connection requests initialized yet.';
            }
        } catch (e) {
            historyLog.textContent = 'Remote connection history un-synchronized.';
        }
    };

    updateHistory();
    // Additional workspace control elements continue via background binding loops safely...
}

document.addEventListener('DOMContentLoaded', () => { load(); });
