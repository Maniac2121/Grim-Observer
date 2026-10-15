#!/usr/bin/env bash
# Run with Godot 4.6.3, its Android export templates, JDK 17+, and Android SDK installed.
set -euo pipefail
cd -- "$(dirname -- "$0")"
: "${ANDROID_HOME:?Set ANDROID_HOME to the installed Android SDK}"
: "${JAVA_HOME:?Set JAVA_HOME to a JDK 17+}"
: "${OBSERVER_KEYSTORE:?Set OBSERVER_KEYSTORE to your release keystore path}"
: "${OBSERVER_KEY_ALIAS:?Set OBSERVER_KEY_ALIAS to your signing alias}"
: "${OBSERVER_KEY_PASSWORD:?Set OBSERVER_KEY_PASSWORD securely; do not commit it}"
command -v godot >/dev/null
command -v python3 >/dev/null
tools_dir=$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)
[[ -x "$tools_dir/apksigner" && -x "$tools_dir/aapt" && -x "$tools_dir/zipalign" ]]
[[ -f "$OBSERVER_KEYSTORE" ]]
mkdir -p dist
# Editor settings and export credentials stay outside versioned source.
python3 - <<'PY'
import os,pathlib,json
root=pathlib.Path(os.environ.get('XDG_CONFIG_HOME',str(pathlib.Path.home()/'.config')))/'godot'
root.mkdir(parents=True,exist_ok=True)
p=root/'editor_settings-4.6.tres'
if p.exists():
 text=p.read_text()
else:
 text='[gd_resource type="EditorSettings" format=3]\n\n[resource]\n'
for k,v in [('export/android/android_sdk_path',os.environ['ANDROID_HOME']),('export/android/java_sdk_path',os.environ['JAVA_HOME'])]:
 lines=[line for line in text.splitlines() if not line.startswith(k+' = ')]
 text='\n'.join(lines)+'\n'+k+' = '+json.dumps(v)+'\n'
p.write_text(text)
PY
export GODOT_ANDROID_KEYSTORE_RELEASE_PATH="$OBSERVER_KEYSTORE"
export GODOT_ANDROID_KEYSTORE_RELEASE_USER="$OBSERVER_KEY_ALIAS"
export GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD="$OBSERVER_KEY_PASSWORD"
godot --headless --path . --import --editor --quit
godot --headless --path . --export-release Android dist/GrimObserver-0.1.0.apk 2>&1 | tee dist/export.log
"$tools_dir/apksigner" verify --verbose --print-certs dist/GrimObserver-0.1.0.apk | tee dist/signature.txt
"$tools_dir/zipalign" -c -P 16 -v 4 dist/GrimObserver-0.1.0.apk > dist/alignment.txt
"$tools_dir/aapt" dump badging dist/GrimObserver-0.1.0.apk > dist/package.txt
python3 - <<'PY'
from pathlib import Path
s=Path('dist/package.txt').read_text()
assert "package: name='ro.grimobserver.standalone20261015'" in s,s
assert 'arm64-v8a' in s,s
assert "package: name='ro.w40k.sim'" not in s
print('Unique package and ARM64 architecture verified.')
PY
sha256sum dist/GrimObserver-0.1.0.apk > dist/GrimObserver-0.1.0.apk.sha256
printf '%s\n' 'APK built, signed, and statically verified. Installation on a device remains a separate check.'
