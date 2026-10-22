#!/bin/bash
# Regression environments are disposable and never attach production resources.
set -Eeuo pipefail

preflight_compose() {
    docker compose -p "$preflight_project" --project-directory "$preflight_snapshot" \
        -f "$preflight_snapshot/deploy/compose.preflight.yml" "$@"
}

preflight_cleanup() {
    local result=$?
    trap - EXIT
    if [[ -n "${preflight_snapshot:-}" ]]; then
        preflight_compose down --rmi local >/dev/null 2>&1 || true
        rm -rf -- "${preflight_work:?}"
    fi
    exit "$result"
}

preflight_failure() {
    local result=$?
    printf 'Preflight failed (exit %s). No activation was requested by this runner.\n' "$result" >&2
    exit "$result"
}

run_preflight() {
    local commit= source_dir script_dir
    if [[ "${1:-}" == --help ]]; then
        printf 'Usage: bash run_preflight_checks.sh --commit FULL_SHA\n'
        return 0
    fi
    [[ $# == 2 && "$1" == --commit && "$2" =~ ^[0-9a-f]{40}$ ]] || {
        printf 'An exact full commit SHA is required.\n' >&2; return 1;
    }
    commit=$2
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    source_dir=${SDS_SOURCE_DIR:-$script_dir}
    if [[ ! -d "$source_dir/.git" && "$source_dir" == /opt/sanders-dash-seal ]]; then
        source_dir=/opt/sds-approved-source
    fi
    python3 "$source_dir/scripts/verify_release_source.py" "$source_dir" "$commit"
    command -v docker >/dev/null
    docker compose version >/dev/null
    preflight_work=$(mktemp -d "${TMPDIR:-/tmp}/sds-preflight.XXXXXX")
    preflight_snapshot="$preflight_work/source"
    preflight_project="sds-preflight-$$-$RANDOM"
    mkdir "$preflight_snapshot"
    trap preflight_cleanup EXIT
    trap preflight_failure ERR
    python3 "$source_dir/scripts/verify_release_source.py" "$source_dir" "$commit" --copy-to "$preflight_snapshot"
    printf 'Preflight source commit: %s\n' "$commit"
    preflight_compose config --quiet
    preflight_compose build --quiet node-tests python-tests
    printf '[Node] Running the actual worker and Python integration tests.\n'
    preflight_compose run --rm --no-deps node-tests
    printf '[Python] Discovering and running the actual unittest suite.\n'
    preflight_compose run --rm --no-deps python-tests
    printf 'LOCAL_REGRESSION_PASSED for %s. Live infrastructure and release authority remain separate checks.\n' "$commit"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then run_preflight "$@"; fi
