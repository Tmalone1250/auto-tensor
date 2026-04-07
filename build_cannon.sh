#!/bin/bash
# build_cannon.sh — Re-verify Optimism #19895 under the new WSL-governed environment
# Runs just build-cannon-client via the corrected target spec.
set -euo pipefail

source ~/.bashrc 2>/dev/null || true
source ~/.profile 2>/dev/null || true
source ~/.cargo/env 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$HOME/go/bin:/usr/local/go/bin:$HOME/.foundry/bin:$PATH"

KONA_ROOT="/mnt/c/Users/malon/Web2 Development/Auto-Tensor/workspace/optimism/rust/kona"
TARGET_SPEC="${KONA_ROOT}/docker/cannon/mips64-unknown-none.json"
IMAGE="us-docker.pkg.dev/oplabs-tools-artifacts/images/cannon-builder:v1.0.0"
WIN_ROOT=$(wslpath -w "${KONA_ROOT}/../")

echo "=== [Re-Verify] Optimism #19895 — cannon-builder target spec fix ==="
echo "KONA_ROOT : ${KONA_ROOT}"
echo "WIN_ROOT  : ${WIN_ROOT}"
echo "TARGET    : ${TARGET_SPEC}"
echo ""

docker.exe run \
  --rm \
  -v "${WIN_ROOT}:/workdir" \
  -w="/workdir" \
  "${IMAGE}" \
  cargo build \
    -Zbuild-std=core,alloc \
    -Zjson-target-spec \
    --target "kona/docker/cannon/mips64-unknown-none.json" \
    -p kona-client \
    --bin kona-client \
    --profile release-client-lto

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo "=== [SUCCESS] kona-client built successfully with corrected target spec. ==="
else
  echo ""
  echo "=== [FAILURE] Build exited with code ${EXIT_CODE}. ==="
fi

exit $EXIT_CODE
