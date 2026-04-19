#!/usr/bin/env bash
set -euo pipefail

EDK2_MNT="${AXIONFW_EDK2_MNT:-/mnt/c/AxionFW/edk2}"
OUT_MNT="${AXIONFW_OUT_MNT:-/mnt/c/AxionFW/Base/out}"
TARGET="${AXIONFW_BUILD_TARGET:-DEBUG}"
TOOLCHAIN="${AXIONFW_TOOLCHAIN:-GCC5}"
PLATFORM_DSC="${AXIONFW_PLATFORM_DSC:-OvmfPkg/OvmfPkgX64.dsc}"
BUILD_TIMEOUT_SECS="${AXIONFW_BUILD_TIMEOUT_SECS:-0}"
REUSE_IF_PRESENT="${AXIONFW_REUSE_IF_PRESENT:-0}"
CLEAN_BUILD="${AXIONFW_CLEAN_BUILD:-0}"
SYNC_SUBMODULES="${AXIONFW_SYNC_SUBMODULES:-0}"
INSTALL_DEPS="${1:-0}"

case "$PLATFORM_DSC" in
  OvmfPkg/OvmfPkgX64.dsc)
    PLATFORM_NAME="OvmfX64"
    ;;
  *)
    echo "[!] Unsupported platform DSC for artifact path inference: $PLATFORM_DSC"
    exit 2
    ;;
esac

BUILD_DIR="$EDK2_MNT/Build/$PLATFORM_NAME/${TARGET}_${TOOLCHAIN}"
FVDIR="$BUILD_DIR/FV"
LOG_PATH="$OUT_MNT/build_${PLATFORM_NAME}_${TARGET}_${TOOLCHAIN}.log"

mkdir -p "$OUT_MNT"
cd "$EDK2_MNT"

if [[ "$INSTALL_DEPS" == "1" ]]; then
  apt-get update -y
  apt-get install -y build-essential gcc g++ make git python3 python3-pip uuid-dev iasl nasm coreutils
fi

git config --global --add safe.directory "$EDK2_MNT" >/dev/null 2>&1 || true
if [[ "$SYNC_SUBMODULES" == "1" ]]; then
  echo "[*] Syncing edk2 submodules"
  git submodule update --init --recursive
else
  echo "[*] Skipping submodule sync (set AXIONFW_SYNC_SUBMODULES=1 to enable)"
fi

make -C BaseTools/Source/C
make -C BaseTools/Source/Python

export WORKSPACE="$EDK2_MNT"
export EDK_TOOLS_PATH="$WORKSPACE/BaseTools"
export PACKAGES_PATH="$WORKSPACE"
export PATH="$EDK_TOOLS_PATH/BinWrappers/PosixLike:$PATH"

if [[ "$REUSE_IF_PRESENT" == "1" ]] && [[ -f "$FVDIR/OVMF_CODE.fd" ]] && [[ -f "$FVDIR/OVMF_VARS.fd" ]]; then
  echo "[*] Reusing existing build artifacts from $FVDIR"
else
  if [[ "$CLEAN_BUILD" == "1" ]]; then
    echo "[*] Removing prior build dir: $BUILD_DIR"
    rm -rf "$BUILD_DIR"
  fi

  BUILD_CMD=(build -a X64 -t "$TOOLCHAIN" -p "$PLATFORM_DSC" -b "$TARGET")
  echo "[*] Running: ${BUILD_CMD[*]}"
  echo "[*] Logging to: $LOG_PATH"

  if [[ "$BUILD_TIMEOUT_SECS" =~ ^[0-9]+$ ]] && [[ "$BUILD_TIMEOUT_SECS" -gt 0 ]]; then
    if timeout "$BUILD_TIMEOUT_SECS" "${BUILD_CMD[@]}" >"$LOG_PATH" 2>&1; then
      build_ec=0
    else
      build_ec=$?
    fi
  else
    if "${BUILD_CMD[@]}" >"$LOG_PATH" 2>&1; then
      build_ec=0
    else
      build_ec=$?
    fi
  fi

  if [[ "$build_ec" -ne 0 ]]; then
    echo "[!] Build failed with exit code $build_ec"
    echo "[!] Last 40 log lines from $LOG_PATH"
    tail -n 40 "$LOG_PATH" || true
    exit "$build_ec"
  fi
fi

if [[ ! -d "$FVDIR" ]]; then
  echo "[!] Expected FV dir missing: $FVDIR"
  exit 3
fi

echo "[*] FV dir: $FVDIR"
for f in OVMF.fd OVMF_CODE.fd OVMF_VARS.fd; do
  if [[ -f "$FVDIR/$f" ]]; then
    cp -f "$FVDIR/$f" "$OUT_MNT/$f"
  else
    echo "[!] Missing expected artifact: $FVDIR/$f"
    exit 4
  fi
done

echo "[OK] Build + copy complete"
echo "[*] Build log: $LOG_PATH"
