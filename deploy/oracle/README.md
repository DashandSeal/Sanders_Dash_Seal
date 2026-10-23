# Oracle Always Free — canonical endpoint observation

Authority: Sanders Dash & Seal Actual Build Design MASTER, sections 3, 6, 7, 19, 20; owner-wide Core Law 10.

The registry records all 38 owner-specified system identities, nicknames, historical host addresses, ports, roles, and six industry-code assignments each. Historical host addresses are **not** asserted to be Oracle compute instance addresses.

Run from a checkout with Python 3:

```sh
python3 deploy/oracle/oracle_registry_probe.py --output /tmp/sanders-oracle-observations.json
python3 -m unittest discover -s tests -p 'test_oracle_registry_probe.py' -v
```

The observer makes concurrent, read-only TCP connections and saves measured outcomes. Reachability is not application health, synthetic intelligence, authorization, or successful deployment. This observer creates no cloud resources and introduces no additional application startup or privileged execution gate.

Next engineering step: connect measurements to the existing durable incident/diagnostic path and OCI instance discovery, then integrate independent, governed recovery and post-repair verification under the original MASTER. No invented signatures, paid resources, or host-IP remapping.
