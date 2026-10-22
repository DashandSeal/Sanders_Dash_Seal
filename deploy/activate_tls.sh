#!/bin/bash
set -Eeuo pipefail
source /opt/sanders-dash-seal/deploy.sh
# Obtain this actual host address through its authenticated primary VNIC.
SDS_PUBLIC_IPV4=$(oci compute instance list-vnics --instance-id "$(curl --noproxy '*' -fsS --max-time 5 -H 'Authorization: Bearer Oracle' http://169.254.169.254/opc/v2/instance/id | tr -d '\"')" --auth instance_principal --region us-phoenix-1 --query 'data[?"is-primary"]."public-ip" | [0]' --raw-output --connection-timeout 5 --read-timeout 10)
python3 -c 'import ipaddress,sys; assert ipaddress.IPv4Address(sys.argv[1]).is_global' "$SDS_PUBLIC_IPV4"
check_dns
# The running HTTP frontend already serves the ACME challenge volume.
compose run --rm --no-deps certbot certonly --non-interactive --keep-until-expiring --webroot --webroot-path=/var/www/certbot --cert-name sandersdashandseal.com -d sandersdashandseal.com -d www.sandersdashandseal.com -d sanderslegalhelpersllc.com -d www.sanderslegalhelpersllc.com -m rooseveltsanders381@gmail.com --agree-tos --no-eff-email
# Atomic configuration file rename requires container recreation to remount it.
if ! cmp -s "$SDS_PROJECT_DIR/nginx.conf" "$SDS_STATE_DIR/nginx.active.conf"; then
    install -m 0644 "$SDS_PROJECT_DIR/nginx.conf" "$SDS_STATE_DIR/nginx.active.conf"
    compose up -d --no-deps --force-recreate reverse-proxy
fi
validate_live
printf 'TLS_ACTIVATED: trusted certificates and HTTPS process checks passed.\n'
