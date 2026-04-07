#!/bin/bash
cd "/mnt/c/Users/malon/Web2 Development/Auto-Tensor/workspace/optimism/rust" || exit
WIN_PATH=$(wslpath -w "$PWD")
docker.exe run --rm -v "${WIN_PATH}:/workdir" -w="/workdir" us-docker.pkg.dev/oplabs-tools-artifacts/images/cannon-builder:v1.0.0 cargo build -Zbuild-std=core,alloc -Zjson-target-spec --target kona/docker/cannon/mips64-unknown-none.json -p kona-client --bin kona-client --profile release-client-lto
