#!/bin/sh
set -eu

[ "${TAXIMOBILE_CRASH_REPORTING_ENABLED:-NO}" = "YES" ] || exit 0

firebase_plist="${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/GoogleService-Info.plist"
if [ ! -f "$firebase_plist" ]; then
  if [ "${TAXIMOBILE_ALLOW_MISSING_FIREBASE_FOR_VERIFICATION:-NO}" = "YES" ]; then
    exit 0
  fi
  echo "error: Crash symbol upload requires the target-matching GoogleService-Info.plist." >&2
  exit 1
fi

crashlytics_script="${BUILD_DIR%/Build/*}/SourcePackages/checkouts/firebase-ios-sdk/Crashlytics/run"
if [ ! -x "$crashlytics_script" ]; then
  echo "error: Firebase Crashlytics symbol upload script is unavailable." >&2
  exit 1
fi

exec "$crashlytics_script"
