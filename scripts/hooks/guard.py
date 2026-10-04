"""Claude Code の PreToolUse フック。守るべき場所への書き込みを実行前に拒否する。

guardrails.md の「お願い」を「強制」に変えるためのもの。.claude/settings.json から呼ばれる。
終了コード 2 で拒否し、stderr の内容がエージェントへの理由として渡される。

Bash / PowerShell のコマンド文字列の検査は完全ではない（書き方次第ですり抜けうる）。
すり抜けた改変は scripts/check.py のロック検査・結果の改変検査が後から検出する。
"""

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

PROTECTED_PATTERNS = [
    "runs/*",
    "papers/*/paper.md",
    ".agent/goal.md",
    ".agent/guardrails.md",
    ".agent/REVIEWER.md",
    ".agent/locks.json",
    ".agent/ADAPT_MODE",
    "lab.config.json",
    "scripts/*",
    ".claude/settings.json",
    ".claude/agents/*",
]

DANGEROUS_SHELL = re.compile(r"\b(rm|mv|cp|del|erase|move|rename|sed\s+-i|Remove-Item|Move-Item|Set-Content|Out-File|tee)\b|>")


def load_config_dirs() -> dict:
    try:
        return json.loads((ROOT / "lab.config.json").read_text(encoding="utf-8"))["dirs"]
    except Exception:
        return {"runs": "runs", "sources": "papers", "agent": ".agent"}


def locked_files() -> set[str]:
    try:
        locks = json.loads((ROOT / load_config_dirs()["agent"] / "locks.json").read_text(encoding="utf-8"))
        return {p for files in locks.values() for p in files}
    except Exception:
        return set()


def to_rel(path_str: str) -> str | None:
    try:
        return Path(path_str).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None


def deny(reason: str) -> None:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    tool = event.get("tool_name", "")
    args = event.get("tool_input", {})
    dirs = load_config_dirs()
    patterns = [p.replace("runs/", dirs["runs"] + "/").replace("papers/", dirs["sources"] + "/") for p in PROTECTED_PATTERNS]

    if tool in ("Bash", "PowerShell"):
        cmd = args.get("command", "")
        if "lock.py" in cmd or "adapt_mode.py" in cmd:
            deny("scripts/lock.py と scripts/adapt_mode.py は人間専用です。実行せず、人間に実行を依頼して止まってください。")

    # 人間が `python scripts/adapt_mode.py on` にしている間は、キットの組み替えのため保護を外す
    if (ROOT / dirs["agent"] / "ADAPT_MODE").exists():
        return

    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        target = args.get("file_path") or args.get("notebook_path") or ""
        rel = to_rel(target)
        if rel is None:
            return
        if rel in locked_files():
            deny(f"{rel} は人間が承認してロックしたファイルです。編集できません。"
                 "変更が必要だと考えた理由を .agent/progress.md に書き、人間に報告して止まってください。")
        for pat in patterns:
            if fnmatch.fnmatch(rel, pat):
                deny(f"{rel} は保護された場所です（{pat}）。"
                     "runs/ は scripts/run.py だけが書き、論文本体・goal・設定・スクリプトは人間だけが編集します。"
                     "詳しくは .agent/guardrails.md を参照してください。")

    elif tool in ("Bash", "PowerShell"):
        cmd = args.get("command", "")
        runs = dirs["runs"]
        if (f"{runs}/" in cmd or f"{runs}\\" in cmd) and DANGEROUS_SHELL.search(cmd):
            deny(f"{runs}/ を変更しうるコマンドは実行できません。{runs}/ は scripts/run.py だけが書く場所です。")


if __name__ == "__main__":
    main()
