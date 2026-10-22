'use strict';
async function loadResources() {
    const status = document.getElementById('resource-status');
    try {
        const response = await fetch('/api/platform/free-resources', {credentials: 'omit', cache: 'no-store'});
        if (!response.ok) throw new Error('Resource mapping unavailable');
        const catalog = await response.json();
        const sources = document.getElementById('resource-sources');
        for (const item of catalog.sources) {
            const row = document.createElement('li');
            const label = document.createElement('strong');
            label.textContent = item.title;
            row.append(label, document.createTextNode(' — ' + item.role));
            sources.append(row);
        }
        const list = document.getElementById('resource-list');
        for (const item of catalog.resources) {
            const card = document.createElement('section');
            card.className = 'card';
            const title = document.createElement('h2');
            title.textContent = item.name;
            const role = document.createElement('p');
            role.textContent = item.platform_role;
            const values = document.createElement('dl');
            for (const [name, value] of Object.entries(item.allowances)) {
                const key = document.createElement('dt');
                key.textContent = name.replaceAll('_', ' ');
                const amount = document.createElement('dd');
                amount.textContent = typeof value === 'number' ? value.toLocaleString() : value;
                values.append(key, amount);
            }
            const notes = document.createElement('ul');
            for (const note of item.conditions) {
                const row = document.createElement('li');
                row.textContent = note;
                notes.append(row);
            }
            card.append(title, role, values, notes);
            list.append(card);
        }
        for (const [name, detail] of Object.entries(catalog.other_services)) {
            const key = document.createElement('dt');
            key.textContent = name.replaceAll('_', ' ');
            const value = document.createElement('dd');
            value.textContent = detail;
            document.getElementById('resource-other').append(key, value);
        }
        status.textContent = catalog.resources.length + ' resource categories mapped. Live account usage has not been queried. No provisioning or spending performed.';
    } catch {
        status.textContent = 'Resource mapping could not be loaded. No cloud changes were made.';
    }
}
loadResources();
