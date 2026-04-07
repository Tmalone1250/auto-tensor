#!/bin/bash
cd "/mnt/c/Users/malon/Web2 Development/Auto-Tensor/workspace/optimism/rust" || exit
docker.exe run \
  --rm \
  -v "$(wslpath -w $(pwd)):/workdir" \
  -w="/workdir" \
  us-docker.pkg.dev/oplabs-tools-artifacts/images/cannon-builder:v1.0.0 cargo build -Zbuild-std=core,alloc -Zjson-target-spec -p kona-client --bin kona-client --profile release-client-lto
