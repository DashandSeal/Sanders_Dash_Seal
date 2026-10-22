#!/bin/bash
# First-boot observation only. No software, firewall or application changes.
set -Eeuo pipefail

collect_system_audit() {
    local architecture timestamp binary target gaps=0
    local -a protected_paths=(/opt/sanders-dash-seal /opt/sds-approved-source /etc/sanders-dash-seal)
    if (( $# )); then protected_paths=("$@"); fi
    printf 'Sanders Dash & Seal system preflight observation\n'
    timestamp=$(date -u '+%Y-%m-%d %H:%M:%S UTC') || return "$?"
    printf 'Timestamp: %s\n' "$timestamp"
    printf '\n[1/4] ARCHITECTURE\n'
    architecture=$(uname -m) || return "$?"
    printf '%s\n' "$architecture"
    printf '\n[2/4] BINARY LOCATIONS\n'
    for binary in git docker oci; do
        if command -v "$binary"; then
            printf '%s: AVAILABLE\n' "$binary"
        else
            printf '%s: NOT_FOUND\n' "$binary"
            gaps=$((gaps + 1))
        fi
    done
    printf '\n[3/4] COMPOSE PLUGIN\n'
    if command -v docker >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
        if timeout 10 docker compose version; then
            printf 'Compose version observed; daemon/application readiness was not tested.\n'
        else
            printf 'Compose version: UNAVAILABLE_OR_TIMED_OUT\n'
            gaps=$((gaps + 1))
        fi
    else
        printf 'Compose version: NOT_CHECKED (docker or timeout missing)\n'
        gaps=$((gaps + 1))
    fi
    printf '\n[4/4] DIRECTORY PERMISSIONS\n'
    for target in "${protected_paths[@]}"; do
        if [[ -d "$target" && ! -L "$target" ]]; then
            if ! stat -c '%A %a %u:%g %n' "$target"; then
                printf 'Permissions unavailable: %s\n' "$target"
                gaps=$((gaps + 1))
            fi
        else
            printf 'Directory missing or symlink requires review: %s\n' "$target"
            gaps=$((gaps + 1))
        fi
    done
    if (( gaps )); then
        printf '\nOBSERVATION_COMPLETE_WITH_GAPS count=%s\n' "$gaps"
    else
        printf '\nOBSERVATION_COMPLETE\n'
    fi
    printf 'This observation does not authorize deployment or establish production readiness.\n'
}

system_audit_main() {
    local log_file=${SDS_SYSTEM_AUDIT_LOG:-/var/log/sds_platform_preflight.log} temporary result=0
    umask 077
    [[ ! -L "$log_file" && ! -L "$(dirname -- "$log_file")" \
       && -d "$(dirname -- "$log_file")" ]] || {
        printf 'Audit log requires an existing nonsymlink directory and nonsymlink file.\n' >&2
        return 1
    }
    temporary=$(mktemp "${log_file}.XXXXXX")
    collect_system_audit > "$temporary" 2>&1 || result=$?
    if ! mv -f -- "$temporary" "$log_file"; then
        rm -f -- "$temporary"
        return 1
    fi
    cat -- "$log_file"
    return "$result"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then system_audit_main "$@"; fi
