# Imperial Jade storefront integration

This additive storefront is designed for the existing Sanders Dash & Seal WSGI application. It does not replace the current appointment, operator, auth or payment handlers.

New files: web/jade-landing.html, web/jade-landing.css, web/jade-landing.js.

**Still required:** Upload the approved founder portrait as web/sds-founder.png (binary asset), wire the /landing route and the three /assets/jade-landing.* paths plus /assets/sds-founder.png in the existing WSGI routing, and generate matching .pbd.json source-hash manifests with the repository's own tooling. Do not fabricate signatures. Verify the existing /appointments, /auth/login, /operator and /stripe/webhook routes remain unchanged.

The customer appointment and Stripe payment flows are development integrations, not verified live production transactions. This branch does not authorize notarial acts or activate unverified RON services. Package prices are distinct from statutory notarial fees.

This branch is a staging integration, not a completed deployment.
