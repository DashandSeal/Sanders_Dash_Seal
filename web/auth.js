/* =========================================================================
 * Module: web/auth.js
 * Architectural Layer: Touch-Responsive Authentication Controller
 * Property of: Sanders Legal Helpers LLC | Developed by: Roosevelt Sanders
 * Custom Platform: Sanders Dash & Seal (Mobile Web / Webview Engine)
 * ========================================================================= */

"use strict";

const el = id => document.getElementById(id);

const modes = {
    login: ['Sign in', 'Sign in to request an appointment and secure documents.'],
    register: ['Create an account', 'Choose an account name and a passphrase to begin.'],
    setup: ['Set up owner access', 'Use your private owner setup secret token to initialize administration.'],
    logout: ['Sign out', 'Sign out of this browser session and its access authorization.']
};

// Continuous cross-platform mobile gesture binder
function bindTouchAction(element, callback) {
    if (!element) return;
    let gestureMoved = false;
    
    element.addEventListener('touchstart', () => { gestureMoved = false; }, { passive: true });
    element.addEventListener('touchmove', () => { gestureMoved = true; }, { passive: true });
    element.addEventListener('touchend', (e) => {
        if (!gestureMoved) {
            e.preventDefault();
            callback(e);
        }
    });
    element.addEventListener('click', (e) => { callback(e); });
}

const mode = location.pathname.split('/').pop().replace('.html', '');
const selected = modes[mode] || modes.login;

// Safely configure DOM view layouts with mobile check bounds
document.addEventListener('DOMContentLoaded', () => {
    const titleNode = el('auth-title');
    const descNode = el('auth-description');
    const submitNode = el('account-submit');
    const formNode = el('account-form');

    if (titleNode) titleNode.textContent = selected[0];
    if (descNode) descNode.textContent = selected[1];
    if (submitNode) submitNode.textContent = selected[0];

    if (mode === 'register' || mode === 'setup') {
        const pwd = el('password');
        if (pwd) pwd.setAttribute('autocomplete', 'new-password');
    }
    if (mode === 'setup') {
        const setupField = el('setup-field');
        if (setupField) setupField.hidden = false;
        const setupToken = el('setup-token');
        if (setupToken) setupToken.required = true;
    }
    if (mode === 'login') {
        const altRef = el('auth-alternative');
        if (altRef) altRef.setAttribute('href', '/auth/login');
    }
    if (mode === 'logout') {
        const usernameField = el('username');
        if (usernameField) usernameField.required = false;
        const passwordField = el('password');
        if (passwordField) passwordField.required = false;
        const accountFields = el('account-fields');
        if (accountFields) accountFields.hidden = true;
    }

    if (formNode) {
        formNode.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!formNode.reportValidity()) return;

            if (submitNode) submitNode.disabled = true;
            const msgNode = el('auth-message');
            if (msgNode) msgNode.textContent = 'Verifying credentials...';

            const payload = {
                username: el('username') ? el('username').value.trim() : '',
                password: el('password') ? el('password').value : ''
            };

            if (mode === 'setup') {
                payload.setup_token = el('setup-token') ? el('setup-token').value : '';
            }

            try {
                const response = await fetch('/auth/' + (mode === 'logout' ? 'logout' : (mode === 'setup' ? 'setup' : (mode === 'register' ? 'register' : 'login'))), {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Authentication loop failed');
                }

                if (msgNode) msgNode.textContent = 'Success. Redirecting...';
                
                // Native mobile webview routing coordination flags
                setTimeout(() => {
                    if (mode === 'logout') {
                        window.location.assign('/auth/login.html');
                    } else if (mode === 'setup' || mode === 'register' || result.role === 'OPERATOR') {
                        window.location.assign('/operator.html');
                    } else {
                        window.location.assign('/index.html');
                    }
                }, 500);

            } catch (error) {
                if (msgNode) msgNode.textContent = error.message === 'try_again_later' ? 'Too many sign-in attempts. Try again shortly.' : 'Sign-in failed. Check details.';
                if (submitNode) submitNode.disabled = false;
            }
        });
    }
});
