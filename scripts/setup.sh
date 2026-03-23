#!/usr/bin/env bash
# ============================================================================
# Weibo QR Login Skill — 一键安装脚本
# 适用于：Ubuntu 22.04+ / Debian 12+（需要已安装 OpenClaw + Node.js 18+）
# 用途：安装 Playwright + Chromium，配置 OpenClaw 浏览器环境
# 使用：bash scripts/setup.sh
# ============================================================================

set -euo pipefail

PLAYWRIGHT_MIRROR="https://npmmirror.com/mirrors/playwright"

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

info()  { echo "[INFO] $*"; }
ok()    { echo "[ OK ] $*"; }
warn()  { echo "[WARN] $*"; }
fail()  { echo "[FAIL] $*"; exit 1; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------------------
# Step 1: 前置检查
# ---------------------------------------------------------------------------

preflight() {
    info "前置检查..."

    [[ "$(uname -s)" == "Linux" ]] || fail "仅支持 Linux（当前: $(uname -s)）"
    has_cmd openclaw               || fail "未找到 openclaw — https://docs.openclaw.ai/"
    has_cmd node                   || fail "未找到 node — 请先安装 Node.js 18+"
    has_cmd npm                    || fail "未找到 npm — 请先安装 Node.js 18+"

    ok "前置检查通过"
}

# ---------------------------------------------------------------------------
# Step 2: 安装 Playwright + Chromium（使用国内镜像）
# ---------------------------------------------------------------------------

install_browser() {
    if has_cmd playwright; then
        ok "Playwright 已安装（$(playwright --version 2>/dev/null)），跳过"
    else
        info "安装 Playwright（Node.js）..."
        npm install -g playwright 2>&1 | tail -1
    fi

    info "安装 Chromium 系统依赖（已安装的会自动跳过）..."
    npx playwright install-deps chromium 2>&1 || warn "install-deps 有警告（通常不影响使用）"

    if npx playwright install chromium --dry-run 2>&1 | grep -q "already installed"; then
        ok "Chromium 已安装，跳过下载"
    else
        info "下载 Chromium（镜像: npmmirror）..."
        PLAYWRIGHT_DOWNLOAD_HOST="$PLAYWRIGHT_MIRROR" npx playwright install chromium
    fi

    local chromium_path
    chromium_path=$(node -e "console.log(require('playwright').chromium.executablePath())" 2>/dev/null || echo "")
    if [[ -z "$chromium_path" || ! -x "$chromium_path" ]]; then
        fail "未找到 Chromium 可执行文件"
    fi

    if [[ "$(readlink -f /usr/local/bin/chromium 2>/dev/null)" == "$chromium_path" ]]; then
        ok "软链接 /usr/local/bin/chromium 已存在，跳过"
    else
        info "创建软链接 /usr/local/bin/chromium -> $chromium_path"
        sudo ln -sf "$chromium_path" /usr/local/bin/chromium
    fi

    ok "浏览器就绪"
}

# ---------------------------------------------------------------------------
# Step 3: 配置 OpenClaw
# ---------------------------------------------------------------------------

configure_openclaw() {
    info "配置 OpenClaw..."

    openclaw config set browser.enabled true
    openclaw config set browser.headless true
    openclaw config set browser.noSandbox true
    openclaw config set browser.defaultProfile openclaw
    openclaw config set browser.profiles.openclaw.cdpPort 18800 --strict-json
    openclaw config set browser.profiles.openclaw.color '"#FF4500"'
    openclaw config set tools.profile full
    openclaw config set tools.deny '[]' --strict-json

    info "重启 gateway..."
    openclaw gateway restart 2>/dev/null || warn "gateway 重启失败，请手动执行: openclaw gateway restart"

    ok "OpenClaw 配置完成"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

main() {
    echo ""
    echo "=== Weibo QR Login Skill — 一键安装 ==="
    echo ""

    preflight
    echo ""
    install_browser
    echo ""
    configure_openclaw

    echo ""
    ok "安装完成！对 Agent 说「获取微博登录二维码」即可使用"
    echo ""
}

main "$@"
