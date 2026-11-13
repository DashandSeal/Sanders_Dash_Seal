# Imperial Jade storefront integration

This additive storefront is designed for the existing Sanders Dash & Seal WSGI application. It does not replace the current appointment, operator, auth or payment handlers.

New files: web/jade-landing.html, web/jade-landing.css, web/jade-landing.js.

**Still required — UPDATE 2026-11-13 (C10, now done):** the three items below
are complete on this branch. The approved founder portrait exists at
`web/sds-founder.png`; the `/landing` route and the three
`/assets/jade-landing.*` paths plus `/assets/sds-founder.png` are wired in
`app/customer_app.py` (lines 24–30); matching `.pbd.json` source-hash manifests
exist for `web/jade-landing.html`, `web/jade-landing.css` and
`web/jade-landing.js`. (The "broken passenger/backend entry point" the
October write-up assumed was rewired November 13, 2026, P0: both entry points
now use the root `wsgi.py` factory, the only `create_native_application` in
the repo.) What remains: no live deployment — this is still a staging
integration, not a completed deployment, and the routes have not been verified
against a running host.

The customer appointment and Stripe payment flows are development integrations, not verified live production transactions. This branch does not authorize notarial acts or activate unverified RON services. Package prices are distinct from statutory notarial fees.

This branch is a staging integration, not a completed deployment.
