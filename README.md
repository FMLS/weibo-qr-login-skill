# Weibo QR Login Skill

A [Cursor Agent Skill](https://docs.cursor.com/context/skills) that automatically fetches a Weibo login QR code via [OpenClaw](https://openclaw.com/) browser integration. After scanning, the browser session retains login cookies for subsequent automation tasks.

## How It Works

1. Starts (or reuses) a browser instance through OpenClaw
2. Navigates to the Weibo QR login page (`https://passport.weibo.com/sso/signin`)
3. Waits for the page to load and locates the QR code image element
4. Extracts the QR code image URL and downloads it as a local PNG file
5. Once the user scans the QR code with the Weibo app, the browser session holds the login state

The entire flow is encapsulated in `scripts/fetch-weibo-qr.py` with built-in retry and error handling logic.

## Prerequisites

- Python 3.9+
- [OpenClaw](https://openclaw.com/) CLI installed and available in `PATH`

## Usage

### As a Cursor Skill

Clone this repository locally and add it as a Skill in Cursor. Then simply ask the Agent to "get a Weibo login QR code" in a conversation — it will automatically run the script and display the QR code image.

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
├── SKILL.md                    # Cursor Skill descriptor defining Agent behavior
├── scripts/
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
