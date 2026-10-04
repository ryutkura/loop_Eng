"""仮説台帳：runs/ から「どの仮説を試し、予測が当たったか」を組み立てる。読むだけで何も書かない。

台帳を別ファイルに持たないのは、エージェントが台帳だけを都合よく書き換えられないようにするため。
runs/ は scripts/run.py しか書けず、改変は check.py が検出する。その runs/ から毎回組み立て直す。

ここで決めること:
  * 仮説の型ごとに、予測が続けて外れた回数（多ければその型は「排除」）
  * 停滞しているか（直近の試行が、それ以前の最良からほとんど近づいていない）＝探索モード
  * 次の実験が許されるか（run.py が実行前に gate() を呼ぶ）
"""

import json

from _lab import d, distance, holds, load_targets

DEFAULT_EXPLORE = {
    "stagnation_window": 3,
    "min_rel_improvement": 0.1,
    "max_failed_predictions_per_type": 2,
    "hypothesis_types": [],
}


def explore_config(config: dict) -> dict:
    return {**DEFAULT_EXPLORE, **config.get("explore", {})}


def normalize_hypothesis(exp: dict) -> dict:
    """実験 JSON の hypothesis を辞書にそろえる。古い形式（文字列だけ）は型「未分類」として扱う。"""
    h = exp.get("hypothesis")
    if isinstance(h, dict):
        return h
    return {"text": h or "", "type": "未分類", "parent": None}


def load_runs(config: dict, paper: str, claim: str) -> list[dict]:
    runs_dir = d(config, "runs")
    out = []
    if not runs_dir.exists():
        return out
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        try:
            meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
            exp = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
            metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # 壊れた run は check.py が別に報告する
        if meta.get("paper") == paper and meta.get("claim") == claim:
            out.append({"name": run_dir.name, "exp": exp, "metrics": metrics})
    return out


def analyze(config: dict, paper: str, claim: str) -> dict:
    ex = explore_config(config)
    target = load_targets(config, paper).get(claim)
    entries = []
    for r in load_runs(config, paper, claim):
        h = normalize_hypothesis(r["exp"])
        e = {
            "run": r["name"],
            "kind": r["exp"].get("kind", "attempt"),
            "type": h.get("type", "未分類"),
            "parent": h.get("parent"),
            "based_on": h.get("based_on"),
            "text": h.get("text", ""),
            "prediction": h.get("prediction"),
            "params": r["exp"].get("params", {}),
            "metrics": r["metrics"],
            "actual": None,
            "distance": None,
            "passed": None,
            "prediction_held": None,
        }
        if e["kind"] == "attempt":
            if target and target["metric"] in r["metrics"]:
                e["actual"] = r["metrics"][target["metric"]]
                e["distance"] = distance(target, e["actual"])
                e["passed"] = e["distance"] == 0.0
            pred = e["prediction"]
            if pred and pred.get("metric") in r["metrics"]:
                e["prediction_held"] = holds(pred, r["metrics"][pred["metric"]])
        entries.append(e)

    attempts = [e for e in entries if e["kind"] == "attempt"]
    diagnostics = [e for e in entries if e["kind"] == "diagnostic"]

    # 型ごとの集計。「予測が外れた」が続いた回数を数え、当たったら 0 に戻す
    types: dict[str, dict] = {}
    for e in attempts:
        s = types.setdefault(e["type"], {"tried": 0, "failed_streak": 0, "last_run": None})
        s["tried"] += 1
        s["last_run"] = e["run"]
        if e["prediction_held"] is False:
            s["failed_streak"] += 1
        elif e["prediction_held"] is True:
            s["failed_streak"] = 0
    exhausted = sorted(t for t, s in types.items() if s["failed_streak"] >= ex["max_failed_predictions_per_type"])

    # 停滞の判定：直近 window 回の最良距離が、それより前の最良距離から min_rel_improvement 以上縮んでいない
    window, eps = ex["stagnation_window"], ex["min_rel_improvement"]
    scored = [e for e in attempts if e["distance"] is not None]
    stagnation = None
    if len(scored) > window and not any(e["passed"] for e in scored):
        before = min(e["distance"] for e in scored[:-window])
        recent = min(e["distance"] for e in scored[-window:])
        if recent > before * (1 - eps):
            stagnation = {"since": scored[-window]["run"], "before": before, "recent": recent}

    return {
        "paper": paper,
        "claim": claim,
        "target": target,
        "explore": ex,
        "entries": entries,
        "attempts": attempts,
        "diagnostics": diagnostics,
        "types": types,
        "exhausted": exhausted,
        "untried": [t for t in ex["hypothesis_types"] if t not in types],
        "stagnation": stagnation,
        "passed": any(e["passed"] for e in attempts),
    }


def _fresh_diagnostic(state: dict, run_name: str | None, newer_than: list[str | None]) -> str | None:
    """based_on が「新しい情報」として有効か。無効なら理由を返す。"""
    if not run_name:
        return "based_on がありません"
    diag = next((e for e in state["diagnostics"] if e["run"] == run_name), None)
    if diag is None:
        return f"based_on の `{run_name}` は、この主張の診断実験（kind: diagnostic）の run ではありません"
    stale = [n for n in newer_than if n and diag["run"] <= n]
    if stale:
        return f"based_on の `{run_name}` は `{stale[0]}` より古く、その後の行き詰まりを踏まえた情報になっていません"
    return None


def gate(config: dict, state: dict, exp: dict) -> list[str]:
    """次の実験を実行してよいか。だめな理由のリストを返す（空なら実行してよい）。"""
    ex = state["explore"]
    budget = config.get("budget", {})
    kind = exp.get("kind", "attempt")
    h = exp.get("hypothesis")
    errors = []

    if kind not in ("attempt", "diagnostic"):
        return [f"kind は attempt（目標に当てにいく試行）か diagnostic（問題の性質を調べる診断）のどちらかです: {kind}"]
    if not isinstance(h, dict):
        return [
            "hypothesis は辞書で書いてください（text・type・parent・prediction・falsified_if）。"
            "形は scripts/run.py の先頭の説明を参照してください。"
        ]

    for key in ("text", "type", "parent"):
        if not h.get(key):
            errors.append(f"hypothesis.{key} がありません。")
    vocab = ex["hypothesis_types"]
    if vocab and h.get("type") not in vocab:
        errors.append(
            f"hypothesis.type `{h.get('type')}` は lab.config.json の explore.hypothesis_types にありません。"
            f"次のどれかを使ってください: {' / '.join(vocab)}。"
            "どれにも当てはまらないなら、型を足すのは人間の仕事なので、止まって報告してください。"
        )

    parent = h.get("parent")
    parent_entry = None
    if parent and parent != "root":
        parent_entry = next((e for e in state["entries"] if e["run"] == parent), None)
        if parent_entry is None:
            errors.append(f"hypothesis.parent `{parent}` は、この主張の run にありません。資料どおりの設定から始めるなら \"root\" と書いてください。")

    if kind == "attempt":
        pred = h.get("prediction")
        if not isinstance(pred, dict) or not {"metric", "op", "value"} <= pred.keys():
            errors.append(
                "hypothesis.prediction がありません。実行する前に、結果がどうなるかを数値で予測してください"
                "（例: {\"metric\": \"median_evals_to_target\", \"op\": \"<=\", \"value\": 1200}）。"
                "外れたら仮説は否定されたとみなします。"
            )
        if not h.get("falsified_if"):
            errors.append("hypothesis.falsified_if がありません。予測が外れたら何を捨てるのかを先に書いてください。")

        limit = budget.get("max_runs_per_claim")
        if limit is not None and len(state["attempts"]) >= limit:
            errors.append(
                f"予算に達しました（試行 {len(state['attempts'])}/{limit}）。"
                "これ以上は回さず、状態表を「再現不可（理由付き）」にするか、人間に報告して止まってください。"
            )

        # 1周1変更：親の設定から変えてよいパラメータは1つまで
        if parent_entry is not None:
            changed = sorted(
                k for k in set(parent_entry["params"]) | set(exp.get("params", {}))
                if parent_entry["params"].get(k) != exp.get("params", {}).get(k)
            )
            if len(changed) > 1:
                errors.append(
                    f"親の run から {len(changed)} 個のパラメータが変わっています（{', '.join(changed)}）。"
                    "1周で変えるのは1つだけです。複数の値を調べたいなら kind: diagnostic の sweep を使ってください。"
                )

        t = h.get("type")
        based_on = h.get("based_on")
        if t in state["exhausted"]:
            last = state["types"][t]["last_run"]
            why = _fresh_diagnostic(state, based_on, [last])
            if why:
                errors.append(
                    f"型「{t}」は予測が {state['types'][t]['failed_streak']} 回続けて外れたので排除されています。"
                    f"この型で続けるには、`{last}` より後の診断実験を based_on に指定してください（{why}）。"
                    f"そうでなければ別の型を選んでください。未試行の型: {' / '.join(state['untried']) or 'なし'}。"
                )
        if state["stagnation"] and t in state["types"]:
            why = _fresh_diagnostic(state, based_on, [state["stagnation"]["since"]])
            if why:
                errors.append(
                    f"探索モードです（停滞を検知: 直近 {ex['stagnation_window']} 回の最良距離 {state['stagnation']['recent']:.3f} が、"
                    f"それ以前の {state['stagnation']['before']:.3f} からほとんど縮んでいません）。"
                    f"すでに試した型「{t}」を続けることはできません（{why}）。次のどれかにしてください: "
                    f"(1) 未試行の型で試す（{' / '.join(state['untried']) or 'なし'}） "
                    f"(2) kind: diagnostic で問題の性質を調べ、その run を based_on にする "
                    f"(3) .agent/REVIEWER.md に従って Reviewer を呼ぶ。"
                )

    else:  # diagnostic
        limit = budget.get("max_diagnostic_runs_per_claim")
        if limit is not None and len(state["diagnostics"]) >= limit:
            errors.append(
                f"診断実験の予算に達しました（{len(state['diagnostics'])}/{limit}）。人間に報告して止まってください。"
            )
        sweep = exp.get("sweep")
        params = exp.get("params", {})
        if not isinstance(sweep, dict) or "param" not in sweep or len(sweep.get("values", [])) < 2:
            errors.append("診断実験には sweep（{\"param\": 調べるパラメータ, \"values\": [2つ以上の値]}）が必要です。")
        elif sweep["param"] not in params:
            errors.append(f"sweep.param `{sweep['param']}` が params にありません。")
        elif parent_entry is not None:
            changed = sorted(
                k for k in set(parent_entry["params"]) | set(params)
                if k != sweep["param"] and parent_entry["params"].get(k) != params.get(k)
            )
            if changed:
                errors.append(
                    f"診断実験では、sweep するパラメータ以外を親の run から変えないでください（変わっているもの: {', '.join(changed)}）。"
                )
    return errors
