/* =========================================================================
 * Module: web/resources.js
 * Architectural Layer: Touch-Responsive Free Resources Inventory Viewer
 * Property of: Sanders Legal Helpers LLC | Developed by: Roosevelt Sanders
 * Description: Dynamically loads and maps active Oracle Always Free allocations
 *              safely inside mobile app WebView layout viewports.
 * ========================================================================= */

"use strict";

const $ = id => document.getElementById(id);

function makeNode(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
}

async function loadResources() {
    const statusNode = $('resource-status');
    const sourcesNode = $('resource-sources');
    const listNode = $('resource-list');

    if (statusNode) statusNode.textContent = 'Synchronizing resource profiles...';

    try {
        const response = await fetch('/api/platform/free-resources', { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Resource directory mapping metrics unavailable');

        const catalog = await response.json();
        
        if (statusNode) statusNode.textContent = '';
        if (sourcesNode) sourcesNode.replaceChildren();
        if (listNode) listNode.replaceChildren();

        // Safe evaluation path over metadata scope parameters
        if (sourcesNode && catalog.scope) {
            const li = makeNode('li', 'sds-metadata-item');
            li.append(makeNode('strong', '', 'Inventory Access: '));
            li.append(document.createTextNode(catalog.scope.replaceAll('_', ' ')));
            sourcesNode.append(li);
        }

        if (!catalog.resources || !Array.isArray(catalog.resources)) {
            if (listNode) listNode.append(makeNode('p', 'sds-empty-msg', 'No documented free tiers discovered.'));
            return;
        }

        // Systematically iterate across your active verified free tier catalog items
        catalog.resources.forEach(item => {
            if (!item) return;

            const card = makeNode('section', 'sds-action-card card');
            card.append(makeNode('h2', 'sds-card-title', item.name || 'Cloud Resource shape'));
            card.append(makeNode('p', 'sds-card-id', `Identifier Hash: ${item.id || 'Unknown'}`));

            if (item.allowances && typeof item.allowances === 'object') {
                const dl = makeNode('dl', 'sds-allowance-list');
                
                for (const [key, value] of Object.entries(item.allowances)) {
                    const dt = makeNode('dt', '', key.toUpperCase().replaceAll('_', ' '));
                    
                    // Safe numeric transformation fence protecting against text parsing crashes
                    const displayValue = (typeof value === 'number' && Number.isFinite(value)) 
                        ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) 
                        : String(value);
                        
                    const dd = makeNode('dd', 'sds-metric-value', displayValue);
                    dl.append(dt, dd);
                }
                card.append(dl);
            }

            if (listNode) listNode.append(card);
        });

        if (statusNode) {
            statusNode.textContent = `Infrastructure Sync Complete. Verified ${catalog.resources.length} free allocation layers.`;
        }

    } catch (error) {
        if (statusNode) {
            statusNode.textContent = 'Resource ledger mapping could not be loaded. Device un-synchronized.';
        }
    }
}

// Dom-Ready mobile initial ingress trigger
document.addEventListener('DOMContentLoaded', () => {
    loadResources();
});
