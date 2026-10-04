"""仮説台帳を表示する。何も書き込まない。外側のループで、次の仮説を決める前に毎回見る。

    python scripts/ledger.py <名前> [<主張ID>]

主張 ID を省くと、targets.json にある全主張を表示する。
表示するもの：試した仮説の一覧（予測と当否）、型ごとの集計、今のモード（通常／探索）、次に許される手、予算。
"""

import sys

from _lab import describe, load_config, load_targets
from _ledger import analyze


def fmt(x, digits: int = 4) -> str:
    if x is None:
        return "―"
    if isinstance(x, bool):
        return "○" if x else "×"
    if isinstance(x, float):
        return f"{x:.{digits}g}"
    return str(x)


def short(run: str | None) -> str:
    """親・根拠の列は先頭の日時だけにする（日時は1行目の run 名の先頭と一致する）。"""
    return run.split("_")[0] if run and run != "root" else (run or "―")


def show(config: dict, paper: str, claim: str) -> None:
    s = analyze(config, paper, claim)
    ex = s["explore"]
    budget = config.get("budget", {})
    print(f"■ {paper} {claim}　目標: {describe(s['target']) if s['target'] else '（targets.json に無い）'}")

    if not s["entries"]:
        print("  まだ run がありません。\n")
        return

    print("| run | 種類 | 型 | 親 | 根拠 | 予測 | 予測の当否 | 実測 | 距離 |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for e in s["entries"]:
        if e["kind"] == "diagnostic":
            sweep = e["metrics"].get("sweep", {})
            values = ", ".join(str(r["value"]) for r in sweep.get("results", []))
            print(f"| {e['run']} | 診断 | {e['type']} | {short(e['parent'])} | ― | {sweep.get('param')} = {values} | ― | ― | ― |")
            continue
        pred = describe(e["prediction"]) if e["prediction"] else "（なし）"
        print(
            f"| {e['run']} | 試行 | {e['type']} | {short(e['parent'])} | {short(e['based_on']) if e['based_on'] else '―'} "
            f"| {pred} | {fmt(e['prediction_held'])} | {fmt(e['actual'])} | {fmt(e['distance'], 3)} |"
        )
    print("  距離 = 合格範囲からの外れ（目標値に対する比）。0 なら合格範囲内。各仮説の文章は runs/<run>/config.json にある。")

    print("\n型ごとの集計:")
    for t, st in s["types"].items():
        mark = "  ← 排除" if t in s["exhausted"] else ""
        print(f"  - {t}: 試行 {st['tried']} 回、予測が続けて外れた回数 {st['failed_streak']}{mark}")
    if s["untried"]:
        print(f"  未試行の型: {' / '.join(s['untried'])}")

    print("\nモード:", end=" ")
    if s["passed"]:
        print("合格済み（PASS した run がある。compare.py の判定が PASS なら状態表を更新する）")
    elif s["stagnation"]:
        st = s["stagnation"]
        print(
            f"探索（停滞を検知。直近 {ex['stagnation_window']} 回の最良距離 {st['recent']:.3f} が、"
            f"それ以前の {st['before']:.3f} から {ex['min_rel_improvement']:.0%} 以上縮んでいない）"
        )
        print("次に許される手（run.py もこれ以外は実行を拒否する）:")
        print(f"  1. 未試行の型で試す: {' / '.join(s['untried']) or 'なし'}")
        print("  2. kind: diagnostic で、効いていそうなパラメータを sweep して問題の性質を調べ、その run を based_on にして続ける")
        print("  3. まず Reviewer を呼ぶ（.agent/REVIEWER.md）。探索モードに入って最初の1回は必ず呼ぶ")
    else:
        print("通常（decisions.md の「未確定」から、予測付きの仮説を1つずつ試す）")
        if s["exhausted"]:
            print(f"  排除された型（新しい診断実験を based_on にしない限り使えない）: {' / '.join(s['exhausted'])}")

    print(
        f"\n予算: 試行 {len(s['attempts'])}/{budget.get('max_runs_per_claim', '∞')}、"
        f"診断 {len(s['diagnostics'])}/{budget.get('max_diagnostic_runs_per_claim', '∞')}\n"
    )


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    config = load_config()
    paper = sys.argv[1]
    claims = [sys.argv[2]] if len(sys.argv) == 3 else list(load_targets(config, paper))
    if not claims:
        print(f"{paper} の targets.json に数値の主張がありません。")
        return 1
    for claim in claims:
        show(config, paper, claim)
    return 0


if __name__ == "__main__":
    sys.exit(main())
