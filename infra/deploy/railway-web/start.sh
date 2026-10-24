#!/bin/sh
set -eu

# Do not pin another environment's resolver or a transient service IP.
resolver=$(awk '$1 == "nameserver" {print $2; exit}' /etc/resolv.conf)
if ! printf '%s' "$resolver" | grep -Eq '^[0-9a-fA-F:.]+$'; then
    echo 'A numeric container DNS resolver is required.' >&2
    exit 1
fi
case "$resolver" in
    *:*) resolver="[$resolver]" ;;
esac
sed "s|@DNS_RESOLVER@|$resolver|g" /etc/nginx/nginx.conf > /tmp/taximobile-nginx.conf
exec nginx -c /tmp/taximobile-nginx.conf -g 'daemon off;'
