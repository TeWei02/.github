#!/usr/bin/env python3
"""TeWei02/.github 社区健康文件仓库自检（零依赖，仅 Python 标准库）。

检查项：
  1. 社区健康文件齐备（双语 README / LICENSE / .gitignore / 行为准则 / 贡献指南 /
     安全政策 / PR 模板 / Issue 模板三件套）
  2. 中英双语 README 双向互链
  3. Markdown 一级标题与本地相对链接是否存在
  4. Issue 模板 YAML 基本结构（顶层 name/description/body，禁用 tab 缩进）
  5. 密钥外泄扫描（高危记 error，可疑硬编码记 warning）
  6. 残留版本冲突标记

退出码：存在 error 时为 1，否则为 0。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_NAME = "TeWei02/.github"
ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    ".gitignore",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "ISSUE_TEMPLATE/bug_report.yml",
    "ISSUE_TEMPLATE/config.yml",
    "ISSUE_TEMPLATE/feature_request.yml",
    "LICENSE",
    "PULL_REQUEST_TEMPLATE.md",
    "README.en.md",
    "README.md",
    "SECURITY.md",
]
# 表单类 Issue 模板必须具备顶层字段；config.yml 仅做基础校验
FORM_TEMPLATES = {"bug_report.yml", "feature_request.yml"}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".yml", ".yaml", ".py", ".js", ".ts", ".html", ".css",
    ".toml", ".ini", ".cfg", ".sh", ".bat", ".ps1", ".xml", ".gitignore", "",
}
MAX_SCAN_BYTES = 2 * 1024 * 1024

MD_LINK_RE = re.compile(r"\]\(\s*([^()\s]+(?:\([^()]*\)[^()\s]*)*)\s*\)")
H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
CONFLICT_RE = re.compile(r"^(<{7}|={7}|>{7})(\s|$)", re.MULTILINE)
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:", re.MULTILINE)

SECRET_RULES = [
    ("私钥块", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"), "error"),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "error"),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "error"),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "error"),
    ("Slack Token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "error"),
    ("OpenAI 风格密钥", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "error"),
]
ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|apikey|secret|secret[_-]?key|token|access[_-]?token|password|passwd)\b"
    r"\s*[:=]\s*[\"'][^\"'\n]{8,}[\"']"
)
PLACEHOLDERS = (
    "your", "xxx", "placeholder", "example", "sample", "changeme", "change-me",
    "todo", "dummy", "fake", "test", "none", "null", "{{", "${",
)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def iter_files() -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            out.append(Path(dirpath) / name)
    return out


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_SCAN_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_required() -> None:
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file():
            err(f"缺少社区健康文件：{name}")


def check_bilingual() -> None:
    zh = ROOT / "README.md"
    en = ROOT / "README.en.md"
    if zh.is_file():
        text = zh.read_text(encoding="utf-8", errors="replace")
        if "README.en.md" not in text:
            err("README.md 未链接英文版 README.en.md")
        if not H1_RE.search(text):
            err("README.md 缺少一级标题")
    if en.is_file():
        text = en.read_text(encoding="utf-8", errors="replace")
        if "README.md" not in text:
            err("README.en.md 未回链中文版 README.md")
        if not H1_RE.search(text):
            err("README.en.md 缺少一级标题")


def resolve_ref(base_dir: Path, target: str) -> Path | None:
    raw = target.strip()
    if not raw or raw.startswith("#"):
        return None
    if any(token in raw for token in ("{{", "}}", "${", "<%", "%}")):
        return None
    parsed = urlsplit(raw)
    if parsed.scheme or raw.startswith("//"):
        return None
    candidate = unquote(raw.split("#", 1)[0].split("?", 1)[0])
    if not candidate:
        return None
    if candidate.startswith("/"):
        return ROOT / candidate.lstrip("/")
    return base_dir / candidate


def check_markdown() -> None:
    for path in iter_files():
        if path.suffix.lower() != ".md":
            continue
        text = read_text(path)
        if text is None:
            continue
        for match in MD_LINK_RE.finditer(text):
            resolved = resolve_ref(path.parent, match.group(1))
            if resolved is None:
                continue
            if not resolved.exists():
                err(f"{rel(path)} 链接指向的文件不存在：{match.group(1)}")


def check_issue_templates() -> None:
    template_dir = ROOT / "ISSUE_TEMPLATE"
    if not template_dir.is_dir():
        err("缺少 ISSUE_TEMPLATE 目录")
        return
    for path in sorted(template_dir.glob("*.yml")) + sorted(template_dir.glob("*.yaml")):
        text = read_text(path)
        if text is None:
            err(f"{rel(path)} 无法按 UTF-8 读取")
            continue
        if not text.strip():
            err(f"{rel(path)} 内容为空")
            continue
        if re.search(r"^\t", text, re.MULTILINE):
            err(f"{rel(path)} 使用了 tab 缩进（YAML 要求空格）")
        top_keys = {m.group(1) for m in TOP_KEY_RE.finditer(text)}
        if path.name == "config.yml":
            if not top_keys & {"blank_issues_enabled", "contact_links"}:
                warn(f"{rel(path)} 未发现 blank_issues_enabled 或 contact_links")
            continue
        for field in ("name", "description"):
            if field not in top_keys:
                err(f"{rel(path)} 缺少顶层字段：{field}")
        if not ({"body", "about"} & top_keys):
            err(f"{rel(path)} 缺少 body 或 about 字段")
        if "body" in top_keys and "labels" not in top_keys:
            warn(f"{rel(path)} 未声明 labels")


def check_secrets() -> None:
    for path in iter_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = read_text(path)
        if text is None:
            continue
        rel_path = rel(path)
        if CONFLICT_RE.search(text):
            err(f"{rel_path} 含未解决的版本冲突标记")
        for label, pattern, level in SECRET_RULES:
            if pattern.search(text):
                (err if level == "error" else warn)(f"{rel_path} 疑似{label}外泄")
        for match in ASSIGN_RE.finditer(text):
            quoted = re.search(r"[\"']([^\"']+)[\"']", match.group(0))
            inner = quoted.group(1).strip().lower() if quoted else ""
            if not inner or any(token in inner for token in PLACEHOLDERS):
                continue
            warn(f"{rel_path} 疑似硬编码凭据赋值：{match.group(1)}")


def main() -> int:
    print(f"== {REPO_NAME} · 社区健康文件自检 ==")
    check_required()
    check_bilingual()
    check_markdown()
    check_issue_templates()
    check_secrets()

    for item in errors:
        print(f"ERROR  {item}")
    for item in warnings:
        print(f"WARN   {item}")
    print(f"\n结果：{len(errors)} error(s), {len(warnings)} warning(s)")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("## 社区健康文件自检\n\n")
            fp.write(f"- error: {len(errors)}\n- warning: {len(warnings)}\n")
            for item in errors:
                fp.write(f"- ERROR: {item}\n")
            for item in warnings:
                fp.write(f"- WARN: {item}\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
