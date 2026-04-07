#!/bin/bash
# Deep WSL tool discovery — sources all common env files
source ~/.bashrc 2>/dev/null || true
source ~/.profile 2>/dev/null || true
source ~/.cargo/env 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$HOME/go/bin:/usr/local/go/bin:$HOME/.foundry/bin:$PATH"

echo "=== WSL Tool Audit ==="
echo "GO:     $(go version 2>&1 | head -1)"
echo "JUST:   $(just --version 2>&1 | head -1)"
echo "RUSTC:  $(rustc --version 2>&1 | head -1)"
echo "FORGE:  $(forge --version 2>&1 | head -1)"
echo "DOCKER: $(docker.exe --version 2>&1 | head -1)"
echo "======================"
