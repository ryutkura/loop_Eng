"""Checker その2：実験結果を、人間が承認した目標値（targets.json）と比べる。何も書き込まない。

    python scripts/compare.py runs/<run フォルダ>

targets.json の形:
{
  "C3": {"metric": "median_evals_to_target", "op": "approx", "value": 1000, "rel_tol": 0.2,
         "source": "表1"}
}
op: "<=" / ">=" / "approx"（value との相対誤差が rel_tol 以内）
"""

import json
import sys

from _lab import ROOT, d, load_config


def judge(target: dict, actual: float) -> tuple[bool, str]:
    op, value = target["op"], target["value"]
    if op == "<=":
        return actual <= value, f"{actual} <= {value}"
    if op == ">=":
        return actual >= value, f"{actual} >= {value}"
    if op == "approx":
        err = abs(actual - value) / abs(value)
        return err <= target["rel_tol"], f"相対誤差 {err:.3f}（許容 {target['rel_tol']}）: 実測 {actual} / 論文 {value}"
    raise ValueError(f"targets.json の op が不正です: {op}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    config = load_config()
    run_dir = ROOT / sys.argv[1]
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    targets_path = d(config, "sources") / meta["paper"] / "targets.json"
    targets = json.loads(targets_path.read_text(encoding="utf-8"))

    claim = meta["claim"]
    if claim not in targets:
        print(f"{claim} の目標値が {targets_path.relative_to(ROOT).as_posix()} にありません。目標値は人間が決めて承認するものです。止まって人間に報告してください。")
        return 2
    target = targets[claim]
    if target["metric"] not in metrics:
        print(f"run の metrics.json に `{target['metric']}` がありません。実験設定の aggregate に追加して実行し直してください。")
        return 2

    ok, detail = judge(target, metrics[target["metric"]])
    print(f"{claim}（{target.get('source', '出典未記入')}）: {'PASS' if ok else 'FAIL'}  {detail}")
    if ok:
        print(f".agent/progress.md の状態表で {claim} を「検証済み」にし、証拠欄に {sys.argv[1]} を書いてください。")
        return 0
    print(
        "合いませんでした。次の順で進めてください：\n"
        "  1. journal/decisions.md の「未確定」の項目のうち、この主張に影響するものを列挙する\n"
        "  2. 最も疑わしい1つを選び、仮説として journal/ の今日のノートに書く\n"
        "  3. その1つだけを変えて、実験をやり直す\n"
        "許容誤差や目標値を変えてはいけません。"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
