# First-boot system observation

The standard cloud-init renderer now embeds `deploy/system_preflight_audit.sh`
as `/usr/local/sbin/sds-system-preflight-audit`. Its single execution chain runs
the observation before the existing pinned, release-authorized bootstrap. This
extends the standard profile; do not paste a separate cloud-config that replaces
the existing bootstrap metadata.

The script records architecture, Git/Docker/OCI executable locations, the Compose
plugin version if available, and directory mode/owner/group for the three known
application/configuration paths. It neither installs packages nor creates those
application directories. The Compose call has a ten-second timeout and does not
claim Docker daemon or application readiness. Missing tools/directories at first
boot produce OBSERVATION_COMPLETE_WITH_GAPS. That means the observation finished,
not that the machine passed deployment requirements. The bootstrap's existing
host, source, runtime and release gates remain in force.

The log is `/var/log/sds_platform_preflight.log`, created with private permissions
and replaced on each run rather than appended indefinitely. Its contents also
appear in cloud-init output. A symlink log is rejected; a real collection or log
write failure returns nonzero. The audit includes directory metadata only, not
private configuration contents, keys, payloads or customer records.

```bash
sudo cat /var/log/sds_platform_preflight.log
sudo tail -f /var/log/cloud-init-output.log
```

For an existing host with this source installed, run the same observation once:

```bash
sudo bash /opt/sanders-dash-seal/deploy/system_preflight_audit.sh
```

The embedded first-boot executable belongs outside `/opt/sanders-dash-seal`.
Writing an untracked script into that managed source tree before staging would
conflict with existing unexpected-file checks. The tracked source version remains
under `deploy/` and participates in source pairing and integrity monitoring.

The owner's submitted cloud-config is preserved in
`docs/owner-submitted/system_audit.proposed.cloud-config.txt`. In a YAML literal
block, shell variables need ordinary `$` characters; the submitted `\$` forms
would print or use literal variable names. The integrated script evaluates its
date, binary names and array correctly at execution time.

This observation supplements the isolated regression preflight, local IMDSv2
helper and six-hour compartment inventory. It does not replace any of them or
prove that provisioning/deployment has occurred. No new instance, cloud-init
change, host command or SSH connection was executed in this development session.
