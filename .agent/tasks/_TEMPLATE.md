# タスク：<名前> の <主張ID>

> `.agent/tasks/<名前>_<主張ID>.md` という名前でコピーして使う。1タスク＝1主張。

## 対象の主張

（claims.md の該当行をそのまま貼る）

## 完了条件

* 性質の主張：`python scripts/check.py` が通り、`tests/<名前>/claims/test_<ID>_*.py` が成功している
* 数値の主張：`python scripts/compare.py` が PASS を返した run がある（または予算内で再現不可と判断した）

## 関係するファイル

* 実装：`src/<名前>/...`
* テスト：`tests/<名前>/claims/...`
* 実験：`experiments/<名前>/...`

## 関係する未確定の点

（journal/decisions.md の ID。例：D1, D3）

## 試した仮説の型

（数値の主張だけ。`python scripts/ledger.py <名前> <主張ID>` の「型ごとの集計」を見て更新する）

## 作業メモ

（試したこと・分かったこと。長くなったら journal/ へ）
