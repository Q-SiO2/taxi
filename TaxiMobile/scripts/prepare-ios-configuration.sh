#!/bin/sh
set -eu

fail() {
  echo "error: $1" >&2
  exit 1
}

role="${TAXIMOBILE_APP_ROLE:-}"
case "$role" in
  PASSENGER|DRIVER) ;;
  *) fail "TAXIMOBILE_APP_ROLE must be PASSENGER or DRIVER." ;;
esac

firebase_source="${SRCROOT}/Configuration/Firebase/${role}/GoogleService-Info.plist"
if [ -f "$firebase_source" ]; then
  configured_bundle_id=$(/usr/libexec/PlistBuddy -c "Print :BUNDLE_ID" "$firebase_source" 2>/dev/null || true)
  [ "$configured_bundle_id" = "${PRODUCT_BUNDLE_IDENTIFIER:-}" ] || \
    fail "The ${role} Firebase plist BUNDLE_ID does not match PRODUCT_BUNDLE_IDENTIFIER."
  resources_directory="${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}"
  mkdir -p "$resources_directory"
  /usr/bin/install -m 600 "$firebase_source" "$resources_directory/GoogleService-Info.plist"
elif [ "${CONFIGURATION:-}" = "Release" ] && \
     [ "${TAXIMOBILE_ALLOW_MISSING_FIREBASE_FOR_VERIFICATION:-NO}" != "YES" ]; then
  fail "Release builds require Configuration/Firebase/${role}/GoogleService-Info.plist."
fi

[ "${CONFIGURATION:-}" = "Release" ] || exit 0

python3_command=$(command -v python3) || fail "Release validation requires python3 on the Xcode host."
"$python3_command" "${SRCROOT}/../scripts/validate_ios_release.py" \
  "${TAXIMOBILE_API_BASE_URL:-}" \
  "${TAXIMOBILE_MAP_STYLE_URL:-}" \
  "${CURRENT_PROJECT_VERSION:-}" \
  "${MARKETING_VERSION:-}" \
  "${TAXIMOBILE_CRASH_REPORTING_ENABLED:-NO}" \
  "${TAXIMOBILE_ALLOW_MISSING_FIREBASE_FOR_VERIFICATION:-NO}"

if [ "${TAXIMOBILE_ALLOW_UNSIGNED_RELEASE_FOR_VERIFICATION:-NO}" != "YES" ]; then
  [ "${CODE_SIGNING_ALLOWED:-YES}" = "YES" ] || \
    fail "Distributable Release builds must enable code signing."
  [ -n "${DEVELOPMENT_TEAM:-}" ] || \
    fail "Distributable Release builds require an externally configured DEVELOPMENT_TEAM."
fi
