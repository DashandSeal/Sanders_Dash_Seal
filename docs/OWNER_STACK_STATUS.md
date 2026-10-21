# Owner-selected stack

The latest supplied worker/package.json, worker/Dockerfile and docker-compose.yml
are applied as written. They supersede the assistant's appointment-only design.

The latest index.js begins mid-handler; its complete source is still required.
The retained prior worker files and package-lock.json do not implement this
selection. No synthesized prefix has been installed.

Select docker-compose.yml explicitly while the previous compose.yaml remains
historical review material. Default Compose commands may choose compose.yaml.
The supplied Dockerfile copies no lockfile before npm ci. The referenced backend
build context and root nginx.conf are also absent. This selection is incomplete;
it has not been built or deployed. Earlier passing tests do not validate it.

No Oracle, DNS, credentials or live production changes were made.
