#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=${MOOS_IVP_WSL_ROOT:-"$HOME/Projects/moos-ivp-wsl"}
[[ "$root" == /* ]] || { echo 'InstallRoot must be an absolute Linux path.' >&2; exit 2; }
jobs=${MOOS_IVP_BUILD_JOBS:-8}
squad=ON
for arg in "$@"; do
  [[ "$arg" == --without-squad ]] && squad=OFF
done
python3 "$here/snapshot.py" --root "$root" "$@"
base="$root/moos-ivp"
common=(-G Ninja -DCMAKE_BUILD_TYPE=Release)

cmake -S "$base/MOOS/MOOSCore" -B "$base/build/MOOS/MOOSCore" "${common[@]}" \
  -DENABLE_EXPORT=OFF -DUPDATE_GIT_VERSION_INFO=ON -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$base/bin"
cmake --build "$base/build/MOOS/MOOSCore" --parallel "$jobs"
cmake -S "$base/MOOS/MOOSEssentials" -B "$base/build/MOOS/MOOSEssentials" "${common[@]}" \
  -DMOOS_DIR="$base/build/MOOS/MOOSCore" -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$base/bin"
cmake --build "$base/build/MOOS/MOOSEssentials" --parallel "$jobs"
cmake -S "$base/MOOS/MOOSGeodesy" -B "$base/build/MOOS/MOOSGeodesy" "${common[@]}" \
  -DENABLE_EXPORT=OFF -DMOOSGEODESY_FETCH_PROJ=auto
cmake --build "$base/build/MOOS/MOOSGeodesy" --parallel "$jobs"
cmake -S "$base/ivp/src" -B "$base/build/ivp" "${common[@]}" \
  -DMOOS_DIR="$base/build/MOOS/MOOSCore" -DMOOSGeodesy_DIR="$base/build/MOOS/MOOSGeodesy" \
  -DIVP_LIB_DIRECTORY="$base/lib" -DIVP_BIN_DIRECTORY="$base/bin" \
  -DIVP_BUILD_GUI_CODE=ON -DIVP_BUILD_SQUAD="$squad"
cmake --build "$base/build/ivp" --parallel "$jobs"
if [[ -d "$root/moos-ivp-mctf/.git" ]]; then
  cmake -S "$root/moos-ivp-mctf" -B "$root/moos-ivp-mctf/build" "${common[@]}" \
    -DMOOS_DIR="$base/build/MOOS/MOOSCore" -DMOOSIVP_SOURCE_TREE_BASE="$base"
  cmake --build "$root/moos-ivp-mctf/build" --parallel "$jobs"
fi
printf '\nBuild complete: %s\n' "$root"
