"""Fail closed unless both actual APKs contain the approved board configuration.

Uses the installed Android SDK apkanalyzer. Build flags and a handwritten
manifest are not evidence of the constants embedded in an APK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

BOARD_API = 'https://alpha-api-staging.up.railway.app'
BOARD_MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'


def sdk_classpath(sdk_root: Path | None = None) -> Path:
    candidates = [sdk_root] if sdk_root else [
        Path(value) for key in ('ANDROID_SDK_ROOT', 'ANDROID_HOME')
        if (value := os.environ.get(key))
    ]
    if not sdk_root and (local_app_data := os.environ.get('LOCALAPPDATA')):
        candidates.append(Path(local_app_data) / 'Android/Sdk')
    for candidate in candidates:
        path = candidate / 'cmdline-tools/latest/lib/apkanalyzer-classpath.jar'
        if path.is_file():
            return path
    raise FileNotFoundError('Android SDK apkanalyzer is unavailable; supply --sdk-root.')


def inspect(apk: Path, sdk_root: Path | None = None) -> dict:
    if not apk.is_file():
        raise FileNotFoundError(f'APK does not exist: {apk}')
    classpath = sdk_classpath(sdk_root)
    java_home = os.environ.get('JAVA_HOME')
    java = Path(java_home) / 'bin/java.exe' if java_home and os.name == 'nt' else None
    executable = str(java) if java and java.is_file() else shutil.which('java')
    if not executable:
        raise FileNotFoundError('Java is required by Android SDK apkanalyzer.')
    result = subprocess.run([
        executable, '-Dcom.android.sdklib.toolsdir=' + str(classpath.parent.parent),
        '-classpath', str(classpath), 'com.android.tools.apk.analyzer.ApkAnalyzerCli',
        'dex', 'code', '--class', 'org.example.taximobile.BuildConfig', str(apk.resolve()),
    ], check=True, capture_output=True, text=True, timeout=45)

    def string(name: str) -> str:
        match = re.search(r'\.field public static final ' + name + r':Ljava/lang/String; = ("[^\n]+")', result.stdout)
        if not match:
            raise ValueError('Missing APK string constant: ' + name)
        return json.loads(match[1])

    def boolean(name: str) -> bool:
        match = re.search(r'\.field public static final ' + name + r':Z = (true|false)', result.stdout)
        if not match:
            raise ValueError('Missing APK boolean constant: ' + name)
        return match[1] == 'true'

    return {
        'api': string('API_BASE_URL'), 'map_style': string('MAP_STYLE_URL'),
        'place_search': boolean('PLACE_SEARCH_ENABLED'),
        'manual_coordinate_entry': boolean('SHOW_MANUAL_COORDINATE_ENTRY'),
        'application_id': string('APPLICATION_ID'), 'role': string('APP_ROLE'),
        'client_version': string('CLIENT_VERSION'),
    }


def require_board_configuration(actual: dict, role: str) -> None:
    if role not in ('passenger', 'driver'):
        raise ValueError('Unknown board role')
    if actual['api'] != BOARD_API:
        raise ValueError('APK does not target board staging')
    if actual['place_search'] or actual['manual_coordinate_entry']:
        raise ValueError('Board APK must use map selection only')
    if actual['map_style'] != BOARD_MAP_STYLE:
        raise ValueError('Unexpected board map style')
    if actual['application_id'] != 'ma.taximobile.' + role or actual['role'] != role.upper():
        raise ValueError('APK role does not match its board artifact')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--passenger-apk', type=Path, required=True)
    parser.add_argument('--driver-apk', type=Path, required=True)
    parser.add_argument('--sdk-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        rows = []
        for role, apk in (('passenger', args.passenger_apk), ('driver', args.driver_apk)):
            actual = inspect(apk, args.sdk_root)
            require_board_configuration(actual, role)
            rows.append({'role': role, 'path': str(apk), 'bytes': apk.stat().st_size,
                         'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'configuration': actual})
        result = json.dumps({'passed': True, 'method': 'Android SDK apkanalyzer dex code', 'artifacts': rows}, indent=2)
        if args.output:
            # Never silently replace a record identifying another candidate.
            with args.output.open('x', encoding='utf-8') as output:
                output.write(result + '\n')
        print(result)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Board APK configuration rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
