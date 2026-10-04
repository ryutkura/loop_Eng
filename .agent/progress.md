# progress — 現在地（State）

> エージェントが更新する。**区切りごとに必ず更新する**こと。
> 会話の記憶は次のセッションに引き継がれない。次の起動はこのファイルだけを頼りに再開する。

## 現在の対象

example_es（キット付属のサンプル）

## 現在のフェーズ

フェーズ4（C1・C2 は検証済み。C3 の外側ループをデモとして残してある）

## 状態表

| 題材 | ID | 状態 | 証拠 | 外側ループの回数 | モード |
| --- | --- | --- | --- | --- | --- |
| example_es | C1 | 検証済み | check / tests/example_es/claims/test_c1_step_size.py | ― | ― |
| example_es | C2 | 検証済み | check / tests/example_es/claims/test_c2_invariance.py | ― | ― |
| example_es | C3 | 未検証 | （`python scripts/run.py experiments/example_es/c3_sphere_10d.json` で確かめられる） | 0 | 通常 |

状態は「未検証」「検証済み」「再現不可」のどれか。再現不可なら、証拠欄に理由と試した run を書く。
モード（数値の主張だけ）は `python scripts/ledger.py <名前> <ID>` の表示をそのまま写す（通常／探索）。自分で決めない。

## 直近の失敗理由

（なし）

## 次の一手

C3：`experiments/example_es/c3_sphere_10d.json` を実行して compare する（「開発再開」で試せるデモ）。
新しい題材を始めるときは「<名前>開発開始」と言う。

## 履歴

| 日時 | 出来事 |
| --- | --- |
| （キット作成時） | サンプル example_es を承認（lock）済み・C1/C2 実装済みの状態で同梱 |
