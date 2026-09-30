"""スクリプト共通の設定読み込み。lab.config.json を唯一の設定元にする。"""

import hashlib
import json
import sys
from pathlib import Path

# Windows の既定（cp932）だと、エージェントが読む出力が文字化けするため UTF-8 に固定する
for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "lab.config.json", encoding="utf-8") as f:
        return json.load(f)


def d(config: dict, key: str) -> Path:
    """lab.config.json の dirs.<key> を絶対パスで返す。"""
    return ROOT / config["dirs"][key]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locks(config: dict) -> dict:
    path = d(config, "agent") / "locks.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
