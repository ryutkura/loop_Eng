# ADAPT — キットを別のプロジェクト用に組み替える手順

「このキットを○○用に書き換えて」と言われたら、この手順に従う。
このキットの**骨格（ループの3条件・書き込み権限・Checker・状態のファイル化）は残し、名前と中身を題材に合わせる**のが目的。

## ステップ1：聞き取り（まとめて1回で聞く）

次を確認する。ユーザーの依頼文から分かるものは聞かずに埋め、推測した内容は「こう解釈しました」と示す。

1. **入力の資料は何か**（論文、仕様書、競技のルール、既存コードの移植元、ベンチマークの定義……）
2. **「完了」を何で判定するか**
   * 性質のテストで判定できる（関数の性質、仕様の条件）
   * 数値の目標で判定する（精度、速度、スコア）
   * 両方
3. **言語とテストの実行方法**（既定は Python の unittest）
4. **重い実行（実験）があるか**。あるなら1回にかかる時間の目安
5. **サンプル（example_es）を残すか消すか**（既定：消す）

## ステップ2：対応表を作って見せる

キットの概念を、そのプロジェクトの言葉に置き換えた表を作り、ユーザーに見せて合意を取る。例：

| キットの概念 | 既定の名前 | このプロジェクトでは |
| --- | --- | --- |
| 入力の資料 | `papers/<名前>/paper.md` | 例：`specs/<名前>/spec.md` |
| 検証できる主張 | `claims.md` | 例：受け入れ条件 |
| 数値の目標 | `targets.json` | 例：性能要件 |
| 外部に依存しない層 | `core/` | 例：`domain/` |
| 実験 | `experiments/` → `runs/` | 例：ベンチマーク |

**名前を変えるのは、意味がずれる時だけ。** 変えなくて済むなら変えない方が、このキットの説明と照らし合わせやすい。

## ステップ3：組み替える

合意が取れたら、次の順で変更する。この作業中に限り、`scripts/`・`lab.config.json`・`.claude/`・`.agent/goal.md` を編集してよい。

**Claude Code で作業している場合**、これらの場所はフック（`scripts/hooks/guard.py`）が書き込みを拒否する。
変更を始める前に、ユーザーに `python scripts/adapt_mode.py on` の実行を依頼して待つ（自分では実行できない）。
Hermes など他のエージェントでは不要。

1. `lab.config.json`
   * `project_name`、`dirs`（フォルダ名を変えたなら実際のフォルダも移動する）
   * `check_commands`（言語に合わせる。例：`["npm", "test"]`、`["cargo", "test"]`、`["pytest", "-q"]`）
   * `pure_layer`（層の名前と、その層で禁止する import。Python 以外なら下記の注意を参照）
   * `budget`（実験が重いなら回数を減らす。`max_diagnostic_runs_per_claim` は診断実験の上限）
   * `explore.hypothesis_types`（仮説の型の一覧。題材で疑う場所の分類に合わせる。細かすぎると排除が効かず、粗すぎると方向転換を強制しすぎる）
   * `explore` の停滞の判定（`stagnation_window`・`min_rel_improvement`・`max_failed_predictions_per_type`）
   * `stats`（`min_seeds`・信頼区間。乱数を使わない題材なら `min_seeds` を 1 にする）
2. `.agent/templates/` の雛形の言葉を題材に合わせる
3. `AGENTS.md` の部屋の地図と合言葉の表を、新しい名前に合わせる（**構造と規則の数は減らさない**）
4. `.agent/goal.md` をこのプロジェクトの目的で書き直す（書いた後、ユーザーに確認してもらう）
5. `.agent/guardrails.md` に題材固有の禁止事項があれば足す
6. サンプルを消す場合：`papers/example_es/`・`src/example_es/`・`tests/example_es/`・`experiments/example_es/` を削除し、
   `.agent/locks.json` から `example_es` の項目を消し、`runs/` の中身と `runs/INDEX.jsonl` を空にする
   （削除の前に、消すものの一覧をユーザーに見せて確認を取る）
7. git が無ければ `git init` して、組み替えた状態を最初のコミットにする

### Python 以外の言語にする場合

* `scripts/` は Python のまま使ってよい（言語に依存するのは `check_commands` と `pure_layer` だけ）
* `check.py` の依存方向の検査は Python の import しか読めない。その言語の仕組み
  （例：ESLint の `no-restricted-imports`、Rust のモジュール公開範囲）に置き換え、`check_commands` に追加する。
  置き換えたら `lab.config.json` の `pure_layer.dir_name` を存在しない名前にして、Python 用の検査を無効にする
* `scripts/run.py` の `entry` は Python の関数を呼ぶ。別言語なら、その言語のプログラムを subprocess で呼び、
  結果の JSON を返す小さな Python 関数を `entry` にする

## ステップ4：健全性の確認

1. `python scripts/check.py` が通ること（サンプルを消した直後は、テストが0件でも通る）
2. `journal/decisions.md` に「K1: キットの組み替え」として、ステップ2の対応表と変更点を記録する
3. ユーザーに次を伝えて終える：
   * 変更したファイルの一覧
   * （Claude Code の場合）`python scripts/adapt_mode.py off` を実行して保護を戻すこと
   * 開発の始め方：「`<名前>開発開始` と言ってください（題材のフォルダが無ければ作ります）」
