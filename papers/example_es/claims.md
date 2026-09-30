# example_es の主張一覧

paper.md から取り出した**検証できる主張**。これが「何ができたら完了か」の定義になる。

* エージェントが下書きし、人間が確認して `python scripts/lock.py example_es` で承認する
* 承認後は**ファイル全体がロックされる**（1文字でも変えると `scripts/check.py` が失敗する）
* 各主張の状態（未検証・検証済み・再現不可）と証拠は、このファイルではなく `.agent/progress.md` の状態表に書く

> 状態の列だけ編集可にすると、主張の文言を「ついでに」書き換えられても気づきにくい。
> そこで「主張の定義（ここ）」と「進捗（progress.md）」をファイルごと分けている。

| ID | 主張 | 出典 | 種類 | 検証方法 |
| --- | --- | --- | --- | --- |
| C1 | 成功率が 1/5 より高ければ σ は増え、低ければ減り、ちょうど 1/5 なら変わらない | 式(2) | 性質 | tests/example_es/claims/test_c1_step_size.py |
| C2 | 目的関数に単調増加な変換をかけても、同じ乱数列なら探索の軌跡が一致する | 4章 | 性質 | tests/example_es/claims/test_c2_invariance.py |
| C3 | 10次元 Sphere で f ≤ 1e-8 到達までの評価回数（5試行の中央値）が約1000回 | 表1 | 数値 | experiments/example_es/c3_sphere_10d.json と targets.json の C3 |
