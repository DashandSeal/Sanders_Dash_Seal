#!/bin/bash
# Owner's production automation profile, integrated with the authorized bootstrap.
set -Eeuo pipefail
initializer_failure() {
    local result=$?
    printf 'Initializer failed (exit %s); activation was not reported as successful.\n' "$result" >&2
    exit "$result"
}
trap initializer_failure ERR

init_fail() { printf 'Initializer stopped: %s\n' "$*" >&2; return 1; }

initialize_instance() {
    local mode=stage selected=0 commit= public_ip= tune=0 script_dir
    while (( $# )); do
        case "$1" in
            --stage|--activate)
                (( selected == 0 )) || init_fail 'Select only one mode.'
                mode=${1#--}; selected=1; shift ;;
            --commit)
                (( $# >= 2 )) || init_fail '--commit requires a value.'
                [[ -z "$commit" ]] || init_fail 'Commit was supplied more than once.'
                commit=$2; shift 2 ;;
            --public-ipv4)
                (( $# >= 2 )) || init_fail '--public-ipv4 requires a value.'
                [[ -z "$public_ip" ]] || init_fail 'Public IPv4 was supplied more than once.'
                public_ip=$2; shift 2 ;;
            --tune-kernel) tune=1; shift ;;
            --help)
                printf 'Usage: bash instance_init.sh [--stage|--activate] --commit FULL_SHA [--public-ipv4 ADDRESS] [--tune-kernel]\n'
                return 0 ;;
            *) init_fail 'Unknown argument.' ;;
        esac
    done
    [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || init_fail 'An exact approved 40-character commit SHA is required.'
    if [[ "$mode" == activate ]]; then
        [[ -n "$public_ip" ]] || init_fail "Activation requires this node's verified public IPv4."
        python3 -c 'import ipaddress,sys; address=ipaddress.IPv4Address(sys.argv[1]); sys.exit(0 if address.is_global else 1)' "$public_ip"
    else
        [[ -z "$public_ip" ]] || init_fail 'Public-IP selection belongs to explicit activation.'
    fi
    export SDS_BOOTSTRAP_COMMIT="$commit" SDS_BOOTSTRAP_MODE="$mode" SDS_TUNE_KERNEL="$tune"
    # An inherited original-host address must never authorize a different node.
    unset SDS_PUBLIC_IPV4
    if [[ "$mode" == activate ]]; then export SDS_PUBLIC_IPV4="$public_ip"; fi
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    printf '[%s] Delegating the pinned release to the existing bootstrap checks.\n' "$mode"
    bash "$script_dir/deploy/sds-bootstrap.sh"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then initialize_instance "$@"; fi
