"""スクリプト共通の設定読み込み。lab.config.json を唯一の設定元にする。"""

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

# Windows の既定（cp932）だと、エージェントが読む出力が文字化けするため UTF-8 に固定する
for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# 種ごとの結果を1つの数値にまとめる関数。run.py（集約）と compare.py（ブートストラップ）が共有する
AGGREGATORS = {
    "mean": statistics.mean,
    "median": statistics.median,
    "min": min,
    "max": max,
    "rate": lambda xs: sum(1 for x in xs if x) / len(xs),
}


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


def load_targets(config: dict, paper: str) -> dict:
    path = d(config, "sources") / paper / "targets.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---- 目標値・予測の判定（targets.json の目標と、実験 JSON の prediction は同じ形） ----
# {"metric": ..., "op": "<=" | ">=" | "approx", "value": ..., "rel_tol": ...（approx のときだけ）}

def band(spec: dict) -> tuple[float, float]:
    """合格になる値の範囲 [下限, 上限]。"""
    op, value = spec["op"], spec["value"]
    if op == "<=":
        return -math.inf, value
    if op == ">=":
        return value, math.inf
    if op == "approx":
        a, b = value * (1 - spec["rel_tol"]), value * (1 + spec["rel_tol"])
        return min(a, b), max(a, b)
    raise ValueError(f"op が不正です: {op}（<= / >= / approx のどれか）")


def holds(spec: dict, actual: float) -> bool:
    lo, hi = band(spec)
    return lo <= actual <= hi


def distance(spec: dict, actual: float) -> float:
    """合格範囲からどれだけ外れているか（目標値に対する相対値）。範囲内なら 0。"""
    lo, hi = band(spec)
    scale = abs(spec["value"]) or 1.0
    if actual < lo:
        return (lo - actual) / scale
    if actual > hi:
        return (actual - hi) / scale
    return 0.0


def describe(spec: dict) -> str:
    if spec["op"] == "approx":
        return f"{spec['metric']} ≈ {spec['value']}（±{spec['rel_tol']:.0%}）"
    return f"{spec['metric']} {spec['op']} {spec['value']}"
