# Weibo QR Login Skill

An [OpenClaw](https://openclaw.com/) skill that fetches a Weibo login QR code via headless browser integration. After scanning, the browser session retains login cookies for subsequent automation tasks.

Compatible with any AI agent platform that supports the OpenClaw skill format (Cursor, OpenClaw Agent, etc.).

## How It Works

1. Starts (or reuses) a browser instance through OpenClaw
2. Navigates to the Weibo QR login page (`https://passport.weibo.com/sso/signin`)
3. Waits for the page to load and locates the QR code image element
4. Extracts the QR code image URL and downloads it as a local PNG file
5. Once the user scans the QR code with the Weibo app, the browser session holds the login state

The entire flow is encapsulated in `scripts/fetch-weibo-qr.py` with built-in retry and error handling logic.

## Prerequisites

- Linux (Ubuntu 22.04+ / Debian 12+)
- [OpenClaw](https://openclaw.com/) CLI installed and running
- Node.js 18+
- Python 3.9+

## Installation

```bash
# Clone the repository
git clone https://github.com/user/weibo-qr-login-skill.git

# Run the one-click setup (Playwright + Chromium + OpenClaw config)
bash weibo-qr-login-skill/scripts/setup.sh
```

The setup script is idempotent and safe to re-run.

## Usage

### Via AI Agent

Add this skill to your agent's workspace, then ask:

> 获取微博登录二维码

The agent will run the script, display the QR code, and guide you through scanning.

### Command Line

```bash
# Default output to /tmp/weibo-qr-<timestamp>.png
python3 scripts/fetch-weibo-qr.py

# Custom output path
python3 scripts/fetch-weibo-qr.py --output ~/Desktop/weibo-qr.png

# Verbose logging
python3 scripts/fetch-weibo-qr.py --verbose
```

## Project Structure

```
weibo-qr-login-skill/
├── SKILL.md                    # Skill descriptor defining agent behavior
├── scripts/
│   ├── setup.sh                # One-click setup (Playwright + Chromium + OpenClaw)
│   └── fetch-weibo-qr.py      # Core script: fetches Weibo login QR code
├── LICENSE                     # MIT License
├── .gitignore
└── README.md
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `openclaw: command not found` | Ensure OpenClaw is installed and in your `PATH` |
| Wrong Python version | Run `python3 --version` to verify >= 3.9 |
| QR code expired | Re-run the script to generate a fresh QR code |
| `gateway closed` error | The script retries automatically and restarts the browser; usually no action needed |

## License

[MIT](LICENSE)
