#!/usr/bin/env python3
"""Weibo Cookie management for OpenClaw browser sessions.

Usage:
    python3 weibo_cookies.py check     # Check if saved cookies are valid
    python3 weibo_cookies.py save      # Fetch cookies from browser and save to disk
    python3 weibo_cookies.py restore   # Load cookies from disk into browser
    python3 weibo_cookies.py export    # Print openclaw browser cookies set commands

Storage: ~/.openclaw/data/weibo/cookies.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

# ── Configuration ────────────────────────────────────────────────

COOKIE_DIR = Path.home() / ".openclaw" / "data" / "weibo"
WEIBO_DOMAINS = ("weibo", "sina")
KEY_COOKIES = ("SUB", "SUBP")  # informational only, not required

# ── Types ────────────────────────────────────────────────────────

CommandRunner = Callable[[list[str]], tuple[int, str]]


@dataclass
class CheckResult:
    valid: bool
    reason: str | None = None
    hours_remaining: float | None = None
    expires_at: str | None = None
    cookie_type: str | None = None
    age_hours: float | None = None
    saved_at: str | None = None
    key_cookies: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None and v != []}


@dataclass
class SaveResult:
    saved: bool
    count: int
    saved_at: str


# ── Pure functions ───────────────────────────────────────────────


def filter_weibo_cookies(cookies: list[dict]) -> list[dict]:
    """Keep only cookies whose domain contains weibo or sina."""
    return [
        c
        for c in cookies
        if any(d in c.get("domain", "") for d in WEIBO_DOMAINS)
    ]


def check_validity(
    cookies: list[dict],
    now: int | None = None,
    meta: dict | None = None,
) -> CheckResult:
    """Validate a cookie list. Pure function — no I/O."""
    if now is None:
        now = int(time.time())

    if not cookies:
        return CheckResult(valid=False, reason="empty_cookies")

    cookie_names = {c["name"] for c in cookies}
    found_keys = [k for k in KEY_COOKIES if k in cookie_names]

    expired_cookie = next(
        (c for c in cookies if c.get("expires", -1) > 0 and c["expires"] < now),
        None,
    )
    if expired_cookie:
        hours_ago = (now - expired_cookie["expires"]) / 3600
        return CheckResult(
            valid=False,
            reason="expired",
            hours_remaining=round(-hours_ago, 1),
            key_cookies=found_keys,
        )

    soonest = min(
        (c for c in cookies if c.get("expires", -1) > 0),
        key=lambda c: c["expires"],
        default=None,
    )
    if soonest:
        remaining = soonest["expires"] - now
        return CheckResult(
            valid=True,
            hours_remaining=round(remaining / 3600, 1),
            expires_at=time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(soonest["expires"])
            ),
            key_cookies=found_keys,
            note="expires_at is the browser-side max lifetime set by Weibo; the server session may expire earlier",
        )

    if meta:
        age_hours = (now - meta.get("saved_ts", now)) / 3600
        return CheckResult(
            valid=True,
            cookie_type="session",
            age_hours=round(age_hours, 1),
            saved_at=meta.get("saved_at"),
            key_cookies=found_keys,
        )

    return CheckResult(valid=True, cookie_type="unknown", key_cookies=found_keys)


def format_export(cookies: list[dict]) -> list[str]:
    """Format cookies as openclaw browser cookies set commands.

    Note: these commands only set name/value/url — they cannot preserve
    httpOnly, sameSite, or expires. For full-fidelity restore use the
    ``restore`` subcommand which goes through Playwright CDP.
    """
    lines: list[str] = []
    for c in cookies:
        scheme = "https" if c.get("secure") else "http"
        domain = c.get("domain", "").lstrip(".")
        path = c.get("path", "/")
        url = f"{scheme}://{domain}{path}"
        lines.append(
            f"openclaw browser cookies set '{c['name']}' '{c['value']}' --url {url}"
        )
    return lines


# ── Storage layer ────────────────────────────────────────────────


class CookieStore:
    """Read/write cookies and metadata to disk."""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._cookie_file = base_dir / "cookies.json"
        self._meta_file = base_dir / "meta.json"

    def exists(self) -> bool:
        return self._cookie_file.exists()

    def load(self) -> list[dict] | None:
        if not self._cookie_file.exists():
            return None
        with open(self._cookie_file) as f:
            return json.load(f)

    def load_meta(self) -> dict | None:
        if not self._meta_file.exists():
            return None
        with open(self._meta_file) as f:
            return json.load(f)

    def save(self, cookies: list[dict]) -> SaveResult:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        saved_at = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(self._cookie_file, "w") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        meta = {
            "saved_at": saved_at,
            "saved_ts": int(time.time()),
            "cookie_count": len(cookies),
            "domains": list({c.get("domain", "") for c in cookies}),
        }
        with open(self._meta_file, "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return SaveResult(saved=True, count=len(cookies), saved_at=saved_at)


# ── Browser bridge ───────────────────────────────────────────────


def default_runner(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


CDP_PORT = 18800


class BrowserBridge:
    """Interact with OpenClaw browser cookies via CLI and Playwright CDP."""

    def __init__(self, run: CommandRunner = default_runner, cdp_port: int = CDP_PORT):
        self._run = run
        self._cdp_port = cdp_port

    def get_cookies(self) -> list[dict]:
        rc, out = self._run(["openclaw", "browser", "cookies"])
        if rc != 0:
            raise RuntimeError(f"Failed to get browser cookies:\n{out.strip()}")
        try:
            cookies = json.loads(out)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Invalid JSON from browser cookies output:\n{out.strip()}"
            )
        if not isinstance(cookies, list):
            raise RuntimeError(
                f"Expected JSON array from browser cookies, got {type(cookies).__name__}"
            )
        return cookies

    def restore_cookies(self, cookies: list[dict]) -> int:
        """Restore cookies via Playwright CDP (preserves all attributes).

        openclaw browser cookies set only supports name/value/url and loses
        httpOnly, sameSite, expires, and domain-dot prefix. Playwright's
        context.addCookies() preserves everything.
        """
        import tempfile

        script = (
            'const{chromium}=require("playwright");\n'
            'const fs=require("fs");\n'
            "(async()=>{\n"
            f'  const raw=fs.readFileSync(process.argv[1],"utf8");\n'
            "  const cookies=JSON.parse(raw).map(c=>({\n"
            '    name:c.name,value:c.value,domain:c.domain,path:c.path||"/",\n'
            "    secure:!!c.secure,httpOnly:!!c.httpOnly,\n"
            '    sameSite:c.sameSite||"None",\n'
            "    expires:c.expires>0?c.expires:undefined\n"
            "  }));\n"
            f'  const browser=await chromium.connectOverCDP("http://127.0.0.1:{self._cdp_port}");\n'
            "  const ctx=browser.contexts()[0]||await browser.newContext();\n"
            "  await ctx.addCookies(cookies);\n"
            "  console.log(JSON.stringify({restored:true,count:cookies.length}));\n"
            "  await browser.close();\n"
            "})().catch(e=>{console.error(e.message);process.exit(1)});\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as sf:
            sf.write(script)
            script_path = sf.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as df:
            json.dump(cookies, df)
            data_path = df.name

        try:
            npm_rc, npm_out = self._run(["npm", "root", "-g"])
            env = f"NODE_PATH={npm_out.strip()} " if npm_rc == 0 else ""
            rc, out = self._run(
                ["bash", "-c", f"{env}node {script_path} {data_path}"]
            )
            if rc != 0:
                raise RuntimeError(
                    f"Cookie restore via Playwright failed:\n{out.strip()}"
                )
            result = json.loads(out.strip().splitlines()[-1])
            return result.get("count", 0)
        finally:
            Path(script_path).unlink(missing_ok=True)
            Path(data_path).unlink(missing_ok=True)


# ── Subcommands ──────────────────────────────────────────────────


def _json_print(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def cmd_check(store: CookieStore) -> int:
    cookies = store.load()
    if cookies is None:
        _json_print({"valid": False, "reason": "no_cookies"})
        return 1

    meta = store.load_meta()
    result = check_validity(cookies, meta=meta)
    _json_print(result.to_dict())
    return 0 if result.valid else 1


def cmd_save(store: CookieStore, bridge: BrowserBridge) -> int:
    raw_cookies = bridge.get_cookies()
    cookies = filter_weibo_cookies(raw_cookies)
    if not cookies:
        _json_print({"saved": False, "reason": "no_weibo_cookies_in_browser"})
        return 1

    result = store.save(cookies)
    _json_print({"saved": result.saved, "count": result.count, "saved_at": result.saved_at})
    return 0


def cmd_restore(store: CookieStore, bridge: BrowserBridge) -> int:
    cookies = store.load()
    if cookies is None:
        _json_print({"restored": False, "reason": "no_cookies"})
        return 1

    count = bridge.restore_cookies(cookies)
    _json_print({"restored": True, "count": count, "total": len(cookies)})
    return 0


def cmd_export(store: CookieStore) -> int:
    cookies = store.load()
    if cookies is None:
        print("ERROR: No saved cookies", file=sys.stderr)
        return 1

    for line in format_export(cookies):
        print(line)
    return 0


# ── CLI entrypoint ───────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Weibo Cookie management for OpenClaw browser sessions."
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="Check if saved cookies are valid")
    sub.add_parser("save", help="Fetch cookies from browser and save to disk")
    sub.add_parser("restore", help="Load cookies from disk into browser")
    sub.add_parser("export", help="Print openclaw browser cookies set commands")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    store = CookieStore(COOKIE_DIR)
    bridge = BrowserBridge()

    dispatch = {
        "check": lambda: cmd_check(store),
        "save": lambda: cmd_save(store, bridge),
        "restore": lambda: cmd_restore(store, bridge),
        "export": lambda: cmd_export(store),
    }
    return dispatch[args.command]()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
