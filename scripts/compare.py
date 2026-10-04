"""Checker その2：実験結果を、人間が承認した目標値（targets.json）と比べる。何も書き込まない。

    python scripts/compare.py runs/<run フォルダ>

targets.json の形:
{
  "C3": {"metric": "median_evals_to_target", "op": "approx", "value": 1000, "rel_tol": 0.2,
         "source": "表1"}
}
op: "<=" / ">=" / "approx"（value との相対誤差が rel_tol 以内）

判定は点推定だけでなく、種のブートストラップで作った信頼区間でも行う（lab.config.json の stats）。
  * 区間がまるごと合格範囲の中     → PASS（終了コード 0）
  * 区間がまるごと合格範囲の外     → FAIL（終了コード 1）
  * 区間が境界をまたぐ・種が少ない → 判定不能（終了コード 3）。乱数のぶれで結果が変わりうる
診断実験（kind: diagnostic）は目標と比べず、値ごとの結果を並べるだけ（終了コード 0）。
"""

import json
import random
import sys

from _lab import AGGREGATORS, ROOT, band, describe, holds, load_config, load_targets

DEFAULT_STATS = {"bootstrap_samples": 2000, "ci": 0.9, "min_seeds": 10}


def bootstrap_interval(values: list, func: str, samples: int, ci: float) -> tuple[float, float]:
    rng = random.Random(0)  # 判定が実行ごとに揺れないよう固定
    n = len(values)
    stats = sorted(AGGREGATORS[func]([values[rng.randrange(n)] for _ in range(n)]) for _ in range(samples))
    lo = stats[int((1 - ci) / 2 * samples)]
    hi = stats[min(samples - 1, int((1 + ci) / 2 * samples))]
    return lo, hi


def show_diagnostic(metrics: dict) -> int:
    sweep = metrics["sweep"]
    print(f"診断実験です（{sweep['param']} を変えたときの振る舞い）。目標とは比べません。")
    names = list(sweep["results"][0]["metrics"]) if sweep["results"] else []
    print("| " + " | ".join([sweep["param"], *names]) + " |")
    print("| " + " | ".join(["---"] * (len(names) + 1)) + " |")
    for r in sweep["results"]:
        print("| " + " | ".join([str(r["value"]), *(f"{r['metrics'][k]:.4g}" for k in names)]) + " |")
    print(
        "\n分かったこと（どの値で何が変わるか・変わらないか）を journal/ の今日のノートに書いてください。"
        "この run を次の試行の hypothesis.based_on に指定できます。"
    )
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    config = load_config()
    stats_cfg = {**DEFAULT_STATS, **config.get("stats", {})}
    run_dir = ROOT / sys.argv[1]
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    exp = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    if exp.get("kind") == "diagnostic":
        return show_diagnostic(metrics)

    targets = load_targets(config, meta["paper"])
    claim = meta["claim"]
    if claim not in targets:
        print(f"{claim} の目標値が {meta['paper']} の targets.json にありません。目標値は人間が決めて承認するものです。止まって人間に報告してください。")
        return 2
    target = targets[claim]
    if target["metric"] not in metrics:
        print(f"run の metrics.json に `{target['metric']}` がありません。実験設定の aggregate に追加して実行し直してください。")
        return 2

    actual = metrics[target["metric"]]
    print(f"{claim}（{target.get('source', '出典未記入')}）: 目標 {describe(target)} / 実測 {actual}")

    # 予測の当否（仮説が否定されたかどうか）。目標の合否とは別に見る
    h = exp.get("hypothesis")
    pred = h.get("prediction") if isinstance(h, dict) else None
    if pred and pred.get("metric") in metrics:
        held = holds(pred, metrics[pred["metric"]])
        print(f"予測: {describe(pred)} → {'的中' if held else '外れ'}（実測 {metrics[pred['metric']]}）")
        if not held:
            print(f"  仮説は否定されました。事前に決めたとおりにしてください: {h.get('falsified_if', '（falsified_if 未記入）')}")

    # 種のぶれを踏まえた判定
    func, key = exp["aggregate"][target["metric"]]
    per_seed = [json.loads(line) for line in (run_dir / "per_seed.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    values = [r[key] for r in per_seed]
    lo, hi = bootstrap_interval(values, func, stats_cfg["bootstrap_samples"], stats_cfg["ci"])
    ok_lo, ok_hi = band(target)
    print(f"ブートストラップ {stats_cfg['ci']:.0%} 区間: [{lo:.4g}, {hi:.4g}]（合格範囲 [{ok_lo:.4g}, {ok_hi:.4g}]、種 {len(values)} 個）")

    if len(values) < stats_cfg["min_seeds"]:
        verdict = "UNSURE"
        reason = f"種が {len(values)} 個で、lab.config.json の stats.min_seeds（{stats_cfg['min_seeds']}）に足りません"
    elif ok_lo <= lo and hi <= ok_hi:
        verdict = "PASS"
    elif hi < ok_lo or lo > ok_hi:
        verdict = "FAIL"
    else:
        verdict = "UNSURE"
        reason = "区間が合格範囲の境界をまたいでいます"

    if verdict == "PASS":
        print(f"判定: PASS\n.agent/progress.md の状態表で {claim} を「検証済み」にし、証拠欄に {sys.argv[1]} を書いてください。")
        return 0
    if verdict == "UNSURE":
        print(
            f"判定: 判定不能（{reason}）。\n"
            "乱数のぶれで PASS にも FAIL にもなりうるので、この結果から次の仮説を立ててはいけません。"
            "params を変えずに seeds だけ増やした実験を、型「統計的ばらつき」・parent をこの run にして回してください。"
        )
        return 3
    print(
        "判定: FAIL\n次の順で進めてください：\n"
        f"  1. `python scripts/ledger.py {meta['paper']} {claim}` で台帳を見て、今が通常モードか探索モードかを確かめる\n"
        "  2. 通常モード：journal/decisions.md の「未確定」から最も疑わしい1つを選び、予測付きの仮説として今日のノートに書く\n"
        "     探索モード：台帳が示す手（未試行の型・診断実験・Reviewer）から選ぶ\n"
        "  3. その1つだけを変えて、実験をやり直す\n"
        "許容誤差や目標値を変えてはいけません。"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
