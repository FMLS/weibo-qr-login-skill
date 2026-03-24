"""weibo_cookies.py 单元测试

BDD 范式，用例按优先级从高到低排列。
"""

from __future__ import annotations

import json

import pytest

from scripts.weibo_cookies import _extract_json_from_output

# ── 测试 fixtures ────────────────────────────────────────────

PLUGIN_LOGS = (
    "[plugins] plugins.allow is empty; discovered non-bundled plugins "
    "may auto-load: adp-openclaw, ddingtalk (+1 more).\n"
    "[adp-openclaw] register() called - starting plugin registration\n"
    "[plugins] [adp-openclaw] Plugin register() called\n"
    "[adp-openclaw] Registering tool factory: adp_upload_file\n"
    "[plugins] [adp-openclaw] Tool adp_upload_file registered successfully\n"
    "[adp-openclaw] Plugin registration complete\n"
    "[plugins] [adp-openclaw] Plugin registration complete\n"
)

PLUGINS_ALLOW_WARNING = (
    "[plugins] plugins.allow is empty; discovered non-bundled plugins "
    "may auto-load: adp-openclaw (+1 more). "
    "Set plugins.allow to explicit trusted ids.\n"
)

SAMPLE_COOKIES = [
    {"name": "SUB", "value": "abc123", "domain": ".weibo.com", "path": "/"},
    {"name": "SUBP", "value": "def456", "domain": ".weibo.com", "path": "/"},
]

SAMPLE_COOKIES_JSON = json.dumps(SAMPLE_COOKIES, indent=2, ensure_ascii=False)

SAMPLE_OBJECT = {"restored": True, "count": 5}
SAMPLE_OBJECT_JSON = json.dumps(SAMPLE_OBJECT)


# ── _extract_json_from_output ────────────────────────────────


class TestExtractJsonFromOutput:
    """从可能混有 gateway 日志的 CLI 输出中提取 JSON"""

    # ── P0：核心保障 ─────────────────────────────────────────

    def test_真实bug复现_gateway日志混在JSON数组之前(self):
        # Given: openclaw browser cookies 的 stdout 前面混入了 plugin 注册日志
        raw = PLUGIN_LOGS + SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 应正确解析出 cookie 数组，忽略日志
        assert result == SAMPLE_COOKIES

    def test_纯净JSON_无日志污染时走快速路径(self):
        # Given: 输出只有干净的 JSON，没有任何日志
        raw = SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 直接解析成功
        assert result == SAMPLE_COOKIES

    def test_stdout日志加stderr警告_前后夹击(self):
        # Given: JSON 前有 stdout plugin 日志，后有 stderr plugins.allow 警告
        #        （模拟 default_runner 将 stdout + stderr 拼接的行为）
        raw = PLUGIN_LOGS + SAMPLE_COOKIES_JSON + "\n" + PLUGINS_ALLOW_WARNING

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 应正确解析出 cookie 数组
        assert result == SAMPLE_COOKIES

    # ── P1：常见变体 ─────────────────────────────────────────

    def test_stderr警告追加在JSON之后(self):
        # Given: JSON 后面拼接了 stderr 的一行警告
        raw = SAMPLE_COOKIES_JSON + "\n" + PLUGINS_ALLOW_WARNING

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 应忽略尾部警告，返回正确数组
        assert result == SAMPLE_COOKIES

    def test_提取JSON对象_用于restore场景(self):
        # Given: Node.js 脚本输出了一个 JSON 对象（restore_cookies 场景）
        raw = PLUGIN_LOGS + SAMPLE_OBJECT_JSON + "\n"

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 应返回 dict
        assert result == SAMPLE_OBJECT

    def test_纯净JSON对象_无日志(self):
        # Given: 只有一个干净的 JSON 对象
        raw = SAMPLE_OBJECT_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 快速路径直接成功
        assert result == SAMPLE_OBJECT

    def test_JSON前后有空白行(self):
        # Given: JSON 周围有额外空行
        raw = "\n\n" + SAMPLE_COOKIES_JSON + "\n\n"

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 应正常解析
        assert result == SAMPLE_COOKIES

    # ── P2：日志格式多样性 ───────────────────────────────────

    def test_带时间戳的日志格式(self):
        # Given: 日志带有时间戳前缀
        logs = (
            "[2026-03-24T12:00:00.000Z] [INFO] Gateway starting\n"
            "[2026-03-24T12:00:01.000Z] [plugins] Loading modules\n"
        )
        raw = logs + SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 时间戳中的方括号不会干扰解析
        assert result == SAMPLE_COOKIES

    def test_日志含有等号和冒号等特殊字符(self):
        # Given: 日志中包含各种特殊字符
        logs = (
            "[config] key=value, port:8080\n"
            "[init] path=/root/.openclaw {mode: production}\n"
        )
        raw = logs + SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 特殊字符不影响 JSON 定位
        assert result == SAMPLE_COOKIES

    def test_紧凑格式JSON_非美化输出(self):
        # Given: JSON 是紧凑格式（单行），前面有日志
        compact = json.dumps(SAMPLE_COOKIES, ensure_ascii=False)
        raw = PLUGIN_LOGS + compact

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 紧凑格式同样能正确解析
        assert result == SAMPLE_COOKIES

    def test_多层嵌套的方括号日志标签(self):
        # Given: 日志标签有嵌套方括号，如 [plugins] [adp-openclaw]
        logs = (
            "[plugins] [adp-openclaw] [subsystem] Nested tags\n"
            "[a] [b] [c] [d] Deep nesting\n"
        )
        raw = logs + SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 嵌套方括号全部被跳过
        assert result == SAMPLE_COOKIES

    def test_日志含有花括号但不是合法JSON(self):
        # Given: 日志中出现了花括号但并非合法 JSON
        logs = (
            "[config] loaded {production} settings\n"
            "[init] process.env = {NODE_ENV: production}\n"
        )
        raw = logs + SAMPLE_COOKIES_JSON

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 非法 JSON 花括号被跳过
        assert result == SAMPLE_COOKIES

    # ── P3：边界与异常 ───────────────────────────────────────

    def test_纯日志无JSON_应抛出异常(self):
        # Given: 输出中完全没有 JSON
        raw = PLUGIN_LOGS

        # When/Then: 应抛出 JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            _extract_json_from_output(raw)

    def test_空字符串_应抛出异常(self):
        # Given: 空输出
        raw = ""

        # When/Then: 应抛出 JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            _extract_json_from_output(raw)

    def test_只有空白字符_应抛出异常(self):
        # Given: 输出只有换行和空格
        raw = "  \n\n  \n"

        # When/Then: 应抛出 JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            _extract_json_from_output(raw)

    def test_空JSON数组仍能正常返回(self):
        # Given: 日志后面跟了一个空数组
        raw = PLUGIN_LOGS + "[]"

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 空数组也是合法 JSON，应返回
        assert result == []

    def test_空JSON对象仍能正常返回(self):
        # Given: 日志后面跟了一个空对象
        raw = PLUGIN_LOGS + "{}"

        # When: 提取 JSON
        result = _extract_json_from_output(raw)

        # Then: 空对象也是合法 JSON，应返回
        assert result == {}
