# ループエンジニアリング・スターターキット

論文などの資料から**検証できる主張**を取り出し、それを満たす実装を**エージェントに自律的に作り続けさせる**ための作業場の雛形です。
Claude Code と Hermes Agent のどちらでも動きます（エージェントへの指示の正本は `AGENTS.md`）。

依存は Python 3.10 以上の標準ライブラリだけです。

---

## 使い方

### 1. コピーして git を始める

このフォルダを好きな場所にコピーし、そこで `git init` しておきます（実験の記録にコミットの ID を残すため）。

### 2. （必要なら）プロジェクトに合わせて組み替える

エージェントに次のように頼みます。

> このディレクトリにはループエンジニアリングの基礎が入っている。〇〇用に書き換えて。

エージェントは `.agent/ADAPT.md` に従って、次の順で進めます。

1. 聞き取り
2. 対応表を見せて合意を取る
3. 組み替える
4. 動作確認

Claude Code では、途中で `python scripts/adapt_mode.py on` の実行を頼まれます。フックの保護を一時的に外すためです。終わったら `off` に戻してください。

論文を実装するだけなら、組み替えずにそのまま使えます。付属のサンプル（`example_es`）は、消すよう頼めば消します。

### 3. 開発を始める

> cmaes開発開始

1. エージェントが `papers/cmaes/` などのフォルダ一式を作って止まります。
2. `papers/cmaes/paper.md` に論文の Markdown を貼り、もう一度「cmaes開発開始」と言います。
3. エージェントが**主張の一覧・目標値・主張ごとのテスト**を下書きして止まります。
4. 中身を確認し、よければ次を実行します。この承認は人間の仕事です。

   ```
   python scripts/lock.py cmaes
   ```

5. 「開発再開」と言うと、ループが回り始めます。

### 4. 放っておく

1回のセッションで最後まで回してほしいときは、`/goal` と組み合わせます（Claude Code・Hermes の両方にあります）。

```text
/goal cmaes開発を再開し、.agent/PROTOCOL.md に従って進める
  until .agent/progress.md の状態表で cmaes の全主張が「検証済み」か「再現不可（理由付き）」になり、
        python scripts/check.py が通り、最後に状態表をそのまま報告している
  without .agent/guardrails.md の禁止事項を破らない
```

何日もかけて回すなら、定期実行と組み合わせます。

* Hermes：`/cron add`
* Claude Code：`claude -p "開発再開"` を OS のタスクスケジューラから呼ぶ

状態はすべてファイルにあるので、毎回新しいセッションで起動しても続きから再開します。

### 状況を知りたいとき

「状況は？」と聞くか、`.agent/progress.md` を開いてください。
経緯は `journal/` に、論文に書かれていない点の解釈は `journal/decisions.md` に残っています。

---

## まずデモで試す

付属のサンプル（1/5 成功則の (1+1)-ES）は、状態が次のようになっています。

* 主張 C1・C2：実装済み
* 主張 C3（数値の再現）：未実行

エージェントに「開発再開」と言うと、C3 の外側ループ（実験 → 比較 → 記録）を1周回すところが見られます。

手で試す場合は次のとおりです。

```
python scripts/check.py
python scripts/run.py experiments/example_es/c3_sphere_10d.json
python scripts/compare.py runs/<できたフォルダ>
python scripts/ledger.py example_es C3
```

---

## フォルダの地図

```text
.
├── AGENTS.md              エージェントへの指示の正本（合言葉・部屋の地図・絶対ルール）
├── CLAUDE.md              AGENTS.md を読み込むだけのポインタ
├── lab.config.json        フォルダ名・テストコマンド・予算・仮説の型・停滞の判定（組み替えの中心）
├── .agent/                🧭 司令室
│   ├── PROTOCOL.md        開発ループの手順（フェーズ0〜5）
│   ├── ADAPT.md           組み替えの手順
│   ├── goal.md            目的と完了の定義（人間だけ）
│   ├── guardrails.md      禁止事項・理由・強制の仕組み（人間だけ）
│   ├── REVIEWER.md        外側のループの独立レビューの手順（人間だけ）
│   ├── progress.md        現在地と状態表（State）
│   ├── tasks/             1主張1タスク
│   ├── templates/         new_paper.py が使う雛形
│   └── locks.json         承認済みファイルのハッシュ（lock.py が書く）
├── papers/<名前>/         📚 論文保管庫（paper.md・claims.md・targets.json）
├── src/<名前>/            🛠 開発室（core/ ＝ 数式、algorithm/ ＝ 組み合わせ）
├── tests/<名前>/          🧪 テスト場（claims/ ＝ 承認済み、unit/ ＝ 自由）
├── sandbox/               🔧 デバッグ場（git 管理外）
├── experiments/<名前>/    🏃 実行場（実験の設定 JSON）
├── runs/                  📦 結果の格納庫（run.py だけが書く）
├── journal/               📓 記録室（日ごとのノート・decisions.md・reviews/）
├── scripts/               ⚙ check / run / compare / ledger / new_paper / lock / adapt_mode
└── .claude/               Claude Code 用の権限とフック（settings.json）・Reviewer（agents/reviewer.md）
```

---

## どう「ループエンジニアリング」になっているか

| ループの部品 | このキットでの担当 |
| --- | --- |
| 終了条件 | 人間が承認した `claims.md` と `targets.json` |
| 進捗（失敗を次の入力に） | `progress.md` の「直近の失敗理由」と、`runs/` から組み立てる仮説台帳（`scripts/ledger.py`） |
| 打ち切り | `lab.config.json` の `budget`（run.py が超過を拒否）、ハーネスのターン上限。「再現不可」も正式な終わり方 |
| Checker（形式） | `scripts/check.py`：ロック・結果の改変・依存方向・テスト |
| Checker（数値） | `scripts/compare.py`：承認済みの目標値との比較。種のブートストラップ区間で「判定不能」も返す |
| State | `progress.md`・`locks.json`・`runs/INDEX.jsonl`（すべてファイル） |
| ループは2重 | 内側：実装 ⇄ check（速い）／外側：実験 ⇄ compare（遅い・1周1変更） |
| 方向転換 | 停滞を検知したら探索モード。試した型の微調整を拒否し、未試行の型か診断実験（`kind: diagnostic`）へ切り替えさせる |
| 新しい情報 | 診断実験（パラメータを sweep して問題の性質を調べる）と、生の記録だけを読む Reviewer（`.agent/REVIEWER.md`） |

### 局所解に陥らないための仕組み

失敗理由だけを次の入力にすると、ループは「前の周の反省から微調整する」だけになり、同じ方向で行き詰まります。
そこで外側のループに次を足しています。

1. **仮説に型・予測・反証条件を付ける**：予測が外れたら仮説は否定されたと判定でき、「もう少し調整すれば」を続けない
2. **予測が続けて外れた型は排除**：`lab.config.json` の `explore.max_failed_predictions_per_type` 回で、その型は使えなくなる
3. **停滞したら探索モード**：直近 `stagnation_window` 回の最良が、それ以前から `min_rel_improvement` 以上近づいていなければ、
   試した型は使えず、未試行の型か診断実験しか回せない
4. **方向を変える根拠は新しい情報**：排除された型でも、その後の診断実験を `based_on` にすれば続けられる
5. **独立した Reviewer**：Proposer の説明ではなく `runs/` の生データから見落としと別の候補を出す

判定はすべて `runs/`（run.py しか書けず、check.py が改変を検出する）から毎回組み立てるので、エージェントが台帳だけを書き換えることはできません。

## 何で守らせているか（強制の範囲）

| 守らせたいこと | Claude Code | Hermes など |
| --- | --- | --- |
| 承認済みの主張・目標値・テストを変えない | フックで**実行前に拒否**＋check で検出 | check で**後から検出** |
| 結果（runs/）を直さない | フックで拒否＋check で検出 | check で検出 |
| lock.py を自分で実行しない | フックと権限設定で拒否 | 文章のみ |
| core/ の依存方向 | check で検出 | check で検出 |
| 1周1変更（params） | run.py が拒否 | run.py が拒否 |
| 予測を書く・排除された型や停滞中の微調整をしない・予算を守る | run.py が拒否 | run.py が拒否 |
| 仮説の型の一覧・Reviewer の基準を変えない | フックで拒否 | 文章のみ（git 差分で確認） |
| 論文に無い選択を記録する／探索モードで Reviewer を呼ぶ／型を正直に申告する | 文章のみ | 文章のみ |

限界も書いておきます。

* フックのシェルコマンド検査は、文字列の照合なので完全ではありません。
* `scripts/` 自体が書き換えられると、検査はすべて無効になります。Hermes で使うときは、`scripts/` の git 差分をときどき確認してください。

詳しくは `.agent/guardrails.md` を見てください。
