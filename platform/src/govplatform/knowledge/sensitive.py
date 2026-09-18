from __future__ import annotations

import re

# 阶段0的"检测"是尽力而为的正则筛查，不是完整的 DLP 系统——能拦住常见的
# 明显情况（手机号、身份证号、"password=xxx"这类赋值），拦不住刻意变形过的
# 敏感信息。库里没有真实敏感数据压力之前，先做到这一层。
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("身份证号", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
    (
        "token/密码/密钥",
        re.compile(r"(?i)\b(password|token|secret|api[_-]?key)\b\s*[:=]\s*\S+"),
    ),
)


def find_sensitive_reason(*texts: str) -> str | None:
    combined = "\n".join(texts)
    for label, pattern in _PATTERNS:
        if pattern.search(combined):
            return label
    return None


def redact(text: str) -> str:
    redacted = text
    for _label, pattern in _PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
