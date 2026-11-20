#!/bin/bash
#--------------------------------------------------------------
#   Script: pr_build.sh
#  Purpose: Build one submodule's pull request in a scratch
#           folder, with the fork's own CMake files and the
#           settings of the build already in build/ivp, without
#           touching the working tree or build/ bin/ lib/.
#
#    Usage: pr_build.sh <submodule> <pr-tree> <overlay> [target ...]
#
#      <submodule>  its directory name under ivp/src (moos-ivp-llm)
#      <pr-tree>    the pull request's version of that submodule,
#                   laid out in scratch (see the pr-review skill)
#      <overlay>    a scratch folder to build in; made if absent,
#                   reused if present (an incremental rebuild)
#      [target]     make targets; by default every library and
#                   executable the pull request's CMake files add
#
#   How: <overlay>/ivp/src is a folder of links to the fork's
#   ivp/src, except that <submodule> points at <pr-tree>. CMake
#   runs there with its output folders set to <overlay>/bin, lib
#   and include, and MOOS taken from the fork's build/MOOS. The
#   libraries the targets need are compiled again in the overlay
#   (a few minutes the first time); nothing is written elsewhere.
#--------------------------------------------------------------
set -u
if [ $# -lt 3 ]; then
  sed -n '3,25p' "$0"; exit 2
fi
SUB="$1"; TREE="$(cd "$2" && pwd -P)"; OVL="$3"; shift 3

HERE="$(cd "$(dirname "$0")" && pwd -P)"
R="$(cd "$HERE/../../.." && pwd -P)"
SRC="$R/ivp/src"
CACHE="$R/build/ivp/CMakeCache.txt"

[ -d "$SRC/$SUB" ]            || { echo "no such submodule: ivp/src/$SUB"; exit 2; }
[ -f "$TREE/CMakeLists.txt" ] || ls "$TREE"/*/CMakeLists.txt >/dev/null 2>&1 \
                              || { echo "no CMakeLists.txt under $TREE"; exit 2; }
[ -f "$CACHE" ]               || { echo "no build in build/ivp to mirror: run ./build.sh first"; exit 2; }
case "$OVL" in
  "$R"/*) echo "the overlay must be outside the repository: $OVL"; exit 2;;
esac

mkdir -p "$OVL/ivp/src" "$OVL/build" "$OVL/bin" "$OVL/lib" "$OVL/include"
OVL="$(cd "$OVL" && pwd -P)"

# The overlay source folder: links to everything, the PR's tree for one
for e in "$SRC"/*; do
  name="$(basename "$e")"
  [ "$name" = "$SUB" ] && continue
  [ -e "$OVL/ivp/src/$name" ] || ln -s "$e" "$OVL/ivp/src/$name"
done
ln -sfn "$TREE" "$OVL/ivp/src/$SUB"

# The settings of the build that is already there
cached() { grep -E "^$1(:[A-Z]+)?=" "$CACHE" | head -1 | cut -d= -f2-; }
CXXFLAGS_REAL="$(cached CMAKE_CXX_FLAGS)"
GUI="$(cached IVP_BUILD_GUI_CODE)";      GUI="${GUI:-ON}"
BOT="$(cached IVP_BUILD_BOT_CODE_ONLY)"; BOT="${BOT:-OFF}"
UTM="$(cached USE_UTM)";                 UTM="${UTM:-ON}"

echo "== configure  (gui=$GUI bot_only=$BOT utm=$UTM)"
echo "   flags: $CXXFLAGS_REAL"
( cd "$OVL/build" && cmake \
    -DIVP_BUILD_GUI_CODE="$GUI" -DFLTK_SKIP_FLUID=ON \
    -DIVP_BUILD_BOT_CODE_ONLY="$BOT" \
    -DIVP_LIB_DIRECTORY="$OVL/lib" -DIVP_BIN_DIRECTORY="$OVL/bin" \
    -DIVP_INC_DIRECTORY="$OVL/include" \
    -DMOOS_DIR="$R/build/MOOS/MOOSCore" \
    -DMOOSGeodesy_DIR="$R/build/MOOS/MOOSGeodesy" \
    -DCMAKE_CXX_FLAGS="$CXXFLAGS_REAL" -DUSE_UTM="$UTM" \
    ${IVP_CMAKE_FLAGS:-} "$OVL/ivp/src" ) > "$OVL/configure.log" 2>&1
if [ $? -ne 0 ]; then
  echo "CONFIGURE FAILED (see $OVL/configure.log)"; tail -25 "$OVL/configure.log"; exit 1
fi

# By default, every target the pull request's CMake files declare
if [ $# -gt 0 ]; then
  TARGETS="$*"
else
  TARGETS="$(grep -rhoiE --include=CMakeLists.txt 'ADD_(EXECUTABLE|LIBRARY) *\( *[A-Za-z0-9_.-]+' "$TREE" \
             | sed -E 's/.*\( *//' | sort -u | tr '\n' ' ')"
fi
[ -n "$TARGETS" ] || { echo "no targets found in $TREE; name them on the command line"; exit 2; }
echo "== build: $TARGETS"

JOBS="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
( cd "$OVL/build" && make -j"$JOBS" $TARGETS ) > "$OVL/build.log" 2>&1
RC=$?

# Diagnostics in the pull request's own files (through the overlay's link or the tree)
DIAG="$(grep -E "(warning|error):" "$OVL/build.log" | grep -E "/$SUB/|$TREE/" | sort -u)"
echo "== compiler diagnostics in $SUB: $( [ -z "$DIAG" ] && echo none || echo "$DIAG" | wc -l )"
[ -n "$DIAG" ] && echo "$DIAG" | cut -c1-260 | head -40

if [ $RC -ne 0 ]; then
  echo "BUILD FAILED (see $OVL/build.log)"; grep -E "error|Error " "$OVL/build.log" | head -20; exit 1
fi
echo "== built into $OVL/bin"
for t in $TARGETS; do
  [ -x "$OVL/bin/$t" ] && echo "   bin/$t"
done
exit 0
