#!/bin/sh
set -eu

osm_url="${GRAPHHOPPER_OSM_URL:-}"
osm_sha256="${GRAPHHOPPER_OSM_SHA256:-}"

case "$osm_url" in
  https://*) ;;
  *) echo "GRAPHHOPPER_OSM_URL must be an explicit HTTPS URL." >&2; exit 2 ;;
esac
case "$osm_url" in
  *'@'*|*'?'*|*'#'*) echo "GRAPHHOPPER_OSM_URL must not contain credentials, a query, or a fragment." >&2; exit 2 ;;
esac
case "$osm_sha256" in
  *[!0-9a-f]*|'') echo "GRAPHHOPPER_OSM_SHA256 must be a lowercase SHA-256 digest." >&2; exit 2 ;;
esac
if [ "${#osm_sha256}" -ne 64 ]; then
  echo "GRAPHHOPPER_OSM_SHA256 must contain exactly 64 characters." >&2
  exit 2
fi

osm_file="/data/morocco-${osm_sha256}.osm.pbf"
graph_directory="/data/graph-v11-${osm_sha256}"
if [ ! -f "$osm_file" ]; then
  partial_file="${osm_file}.partial.$$"
  trap 'rm -f "$partial_file"' EXIT HUP INT TERM
  curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 --retry 3 \
    --output "$partial_file" "$osm_url"
  echo "${osm_sha256}  ${partial_file}" | sha256sum --check --strict
  chmod 0444 "$partial_file"
  mv "$partial_file" "$osm_file"
  trap - EXIT HUP INT TERM
else
  echo "${osm_sha256}  ${osm_file}" | sha256sum --check --strict
fi

exec java -Xms512m -Xmx3g \
  "-Ddw.graphhopper.datareader.file=${osm_file}" \
  "-Ddw.graphhopper.graph.location=${graph_directory}" \
  -jar /opt/graphhopper/graphhopper-web.jar \
  server /opt/graphhopper/config.yml
