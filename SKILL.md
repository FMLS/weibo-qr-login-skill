---
name: weibo-qr-login-skill
description: Fetch Weibo login QR code via OpenClaw browser integration. Use when the user asks to log in to Weibo or needs a Weibo QR code. Runs a Python script that handles browser startup, page navigation, QR extraction, and retry logic automatically.
---

# Weibo QR Login

Always run `scripts/fetch-weibo-qr.py` from this skill's directory to fetch the QR code.

## Required Behavior

- Resolve the script path relative to the directory containing this SKILL.md: `scripts/fetch-weibo-qr.py`.
- The script encapsulates browser startup, page polling, QR URL extraction, and retry logic. **Do not** break it into individual `openclaw browser ...` commands.
- **Do not** fall back to a manual flow — manual steps lose the built-in retry and error handling.

## Setup

Run the setup script before first use to install Playwright + Chromium and configure OpenClaw (idempotent, safe to re-run):

```bash
bash <SKILL_DIR>/scripts/setup.sh
```

## Quick Start

```bash
# <SKILL_DIR> = absolute path to the directory containing this SKILL.md
python3 <SKILL_DIR>/scripts/fetch-weibo-qr.py
```

## Options

```bash
# Custom output path
python3 <SKILL_DIR>/scripts/fetch-weibo-qr.py --output /tmp/my-qr.png

# Verbose logs
python3 <SKILL_DIR>/scripts/fetch-weibo-qr.py --verbose
```

## After QR Code Is Generated

On success the script prints the local path of the QR PNG. The agent **must** then:

1. **Show the image to the user**: Use image preview to display the QR PNG so the user can scan it directly.
2. **Warn about expiration**: Tell the user the QR code expires in ~1–3 minutes and to scan promptly with the Weibo app (Me → Scan).
3. **Wait for confirmation**: Ask the user whether the scan succeeded.
4. **Handle expiration**: If the user reports the code has expired, rerun the script to generate a fresh QR code.

## Troubleshooting (Script Invocation Only)

- If command not found: ensure `openclaw` is in `PATH`.
- If Python missing: use `python3 --version` to verify (requires Python 3.9+).
- If QR expires: rerun the same Python script to generate a new code.
