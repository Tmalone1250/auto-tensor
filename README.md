<div align="center">
  
<img src="./ui/public/auto-tensor.png" width="160" height="160" alt="Auto-Tensor Logo" />

# ⚡ Auto-Tensor

**Autonomous Bittensor Mining Agent · Open-Source SRE Operator**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![WSL](https://img.shields.io/badge/Runs%20In-WSL%202-0078D6?style=for-the-badge&logo=linux&logoColor=white)](https://learn.microsoft.com/en-us/windows/wsl/)
[![GitHub API](https://img.shields.io/badge/GitHub-API%20v3-181717?style=for-the-badge&logo=github&logoColor=white)](https://docs.github.com/en/rest)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-22c55e?style=for-the-badge)]()

_A surgical, multi-agent system that scouts high-value GitHub issues across blockchain infrastructure repos, reproduces them, authors fixes, and stages production-grade PRs — autonomously._

</div>

---

## 🧠 What Is Auto-Tensor?

**Auto-Tensor** is a Bittensor mining agent operating as a **Lead Systems Reliability Engineer** across top-tier Web3 infrastructure repositories — including **MetaMask**, **Optimism**, and **Bitcore**.

It follows a strict, four-phase workflow loop:

```
Scout  ──▶  Coder  ──▶  Reviewer  ──▶  Governor Gate  ──▶  PR
  │            │              │                │
  │            │              │                └── Rate-limit protection
  │            │              └── Audit: side-effects, density, verify
  │            └── Reproduce before/after; apply surgical patch
  └── Hunt: bug / performance / a11y / TypeScript labels
```

Every action is governed by a **rate-limit governor** that enforces miner priority — if quota drops below 15%, all agent activity halts automatically.

---

## 📸 Screenshots

### Neuro-SRE Command Console (v1.0)
![Auto-Tensor Dashboard](./ui/public/auto-tensor_screenshot.png)

_The 'Industrial Sovereign' dashboard provides real-time miner telemetry, GitHub Governor status, and surgical simulation audits._

---

## 🏗️ Architecture

```
auto-tensor/
├── agents/
│   ├── scout.py          # SurgicalScoutV3 — GitHub issue hunter & scorer
│   ├── coder.py          # Reproduction engine — before/after build states
│   └── reviewer.py       # Auditor — side-effects, density, verification
├── core/
│   ├── executor.py       # WSL Mandate Enforcer — all shell via wsl bash
│   └── health_check.py   # The Governor — rate-limit gate & miner priority
├── logs/
│   ├── scout_report.json # Latest scan results
│   └── simulation_audit.md
├── workspace/            # Cloned target repos live here (gitignored)
├── config.yaml           # Watchlist, labels, scout settings
├── build_cannon.sh       # Re-verify Optimism #19895 cannon-builder fix
├── check_deps.py         # Full environment audit (venv + WSL tools)
├── requirements.txt
└── .env                  # GITHUB_PAT, GEMINI_API_KEY
```

---

## 🎯 Targeting Criteria

The Scout evaluates every open issue across the watchlist repos and assigns a **Delta Score (1–10)**:

| Signal                                   | Score Impact |
| ---------------------------------------- | ------------ |
| Base score                               | `+5`         |
| TypeScript `any` / missing interface     | `+3`         |
| `performance` label                      | `+2`         |
| `bug` label                              | `+1`         |
| High comment count (> 10) — competed out | `−1`         |
| Cap                                      | `max 10`     |

**Filtered watchlist:**

| Repo                          | Domain                           |
| ----------------------------- | -------------------------------- |
| `ethereum-optimism/optimism`  | L2 infrastructure, Rust/Go       |
| `MetaMask/metamask-extension` | Browser wallet, TypeScript       |
| `bitpay/bitcore`              | Bitcoin full-node library, JS/TS |

---

## 🛡️ The Governor

`core/health_check.py` is the system's circuit breaker. It runs before every agent action.

```
GitHub Core API Quota
        │
        ▼
  remaining ≥ 750?  ──YES──▶  HEARTBEAT_OK  ──▶  Agents cleared
        │
       NO
        ▼
  HEARTBEAT_LOW ──▶  Sleep until reset + 60s buffer ──▶  Re-check
```

> **Miner Priority Rule:** Any network failure during the health check defaults to a **full halt** of all Scout/Coder activity. The miner is never starved of quota.

---

## 🚀 Quick Start

### Prerequisites

- Windows with **WSL 2** (Ubuntu recommended)
- Python 3.12+ inside WSL
- Docker Desktop (for cannon builds)
- A GitHub Personal Access Token with `repo` + `read:org` scopes

### 1. Clone & Enter WSL

```bash
git clone git@github.com:Tmalone1250/auto-tensor.git
cd auto-tensor
```

### 2. Bootstrap the Virtual Environment

> All Python execution **must** go through `.venv/bin/python` per system mandate.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env:
#   GITHUB_PAT=ghp_...
#   GEMINI_API_KEY=...
```

### 4. Verify Environment

```bash
.venv/bin/python check_deps.py
```

Expected output:

```
==================================================
  Auto-Tensor Environment Audit v2
==================================================

[-- Python Environment --]
[OK]  Virtual Environment: ACTIVE
[OK]  python-dotenv: .env loaded

[-- Python Packages --]
[OK]  requests: 2.33.1
[OK]  PyYAML: 6.0.3

[-- System Tools (WSL) --]
[OK]  Go: go version go1.21.x ...
[OK]  Docker: Docker version 24.x ...
==================================================
```

---

## 🔄 Running the Workflow

### Phase 1 — Scout

Scan all watchlist repos and generate `logs/scout_report.json`:

```bash
.venv/bin/python agents/scout.py
```

### Phase 2 — Coder

Reproduce the bug and verify the fix:

```bash
.venv/bin/python agents/coder.py
```

Outputs:

- `logs/before_build.log` — unpatched failure
- `logs/after_build.log` — patched success

### Phase 3 — Reviewer

Full audit: side-effect check, surgical density, re-verification build:

```bash
.venv/bin/python agents/reviewer.py
```

### Manual Re-Verify (Cannon Build)

```bash
# From WSL
bash build_cannon.sh
```

---

## 📋 Operational Constraints

| Rule                    | Detail                                                                          |
| ----------------------- | ------------------------------------------------------------------------------- |
| **WSL Mandate**         | Every shell command routes through `wsl bash`. No PowerShell, no CMD.           |
| **venv Isolation**      | All Python runs via `.venv/bin/python`. Never the system Python.                |
| **`any` Ban**           | TypeScript repos: primary mission is replacing `any` with precise interfaces.   |
| **Surgical Density**    | PRs must change ≤ 20 lines. No fluff.                                           |
| **Zero Formatting PRs** | Prettier/lint-only changes are prohibited.                                      |
| **No Float Math**       | Any value representing currency or measurement uses integer/Decimal arithmetic. |

---

## 📊 Current Mission Log

### Active Target: `ethereum-optimism/optimism#19895`

> **`bug(kona): kona-host-client-offline-cannon test crashes due to wrong target spec in cannon-builder:v1.0.0`**

| Phase              | Status                                                          |
| ------------------ | --------------------------------------------------------------- |
| Scout              | ✅ Identified — Delta Score 6/10                                |
| Reproduce (Before) | ✅ Non-zero exit confirmed                                      |
| Patch              | ✅ `--target kona/docker/cannon/mips64-unknown-none.json` added |
| Reproduce (After)  | ✅ Exit 0, `kona-client` binary emitted                         |
| Reviewer Audit     | ✅ 6-line delta · 0 side-effects · verification passed          |
| PR                 | 🔜 Staged                                                       |

**Fix summary:** The `cannon-builder:v1.0.0` Docker image is a cross-compile-only toolchain. Without an explicit `--target` pointing to the custom MIPS64 bare-metal JSON spec, `cargo` resolves to the host triple and fails. The fix adds `--target kona/docker/cannon/mips64-unknown-none.json` to the `justfile` recipe and `cannon-repro.dockerfile`.

---

## 🔐 SSH & Git Setup (WSL)

```bash
# Configure identity
git config --global user.name "Trevor Malon"
git config --global user.email "malonetrevor12@gmail.com"

# Generate Ed25519 key
ssh-keygen -t ed25519 -C "malonetrevor12@gmail.com" -f ~/.ssh/id_ed25519 -N ""

# Add GitHub to known_hosts
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts

# Verify
ssh -T git@github.com
# Expected: Hi Tmalone1250! You've successfully authenticated...
```

---

## 📦 Dependencies

| Package         | Version   | Purpose                      |
| --------------- | --------- | ---------------------------- |
| `requests`      | 2.33.1    | GitHub API calls             |
| `PyYAML`        | 6.0.3     | `config.yaml` parsing        |
| `python-dotenv` | 1.2.2     | `.env` loading               |
| `urllib3`       | 2.6.3     | HTTP transport               |
| `certifi`       | 2026.2.25 | TLS certificate verification |

---

## 🤝 Contributing

This is a miner-grade, production system. PRs must pass all three reviewer audits:

1. **Side-Effect Clean** — only expected files changed
2. **Surgical Density** — ≤ 20 lines changed
3. **Verification Build** — after-state exits 0

---

## 📄 License

MIT © [Trevor Malon](https://github.com/Tmalone1250)

---

<div align="center">

_Built for the Bittensor network — where code quality is the proof of work._

</div>
