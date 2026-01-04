# アーキテクチャ設計

## 概要
Interleaving を「ランキング結果を返す直前」への差し込みとして実装し、既存ロジックへの影響を最小化します。

## 構造設計

### 差し込みポイント
Lambda 内の最終段（ランキングリスト生成後、レスポンス返却前）で処理をフックします。

1. **設定取得**: SSM Parameter Store から実験設定を取得（TTLキャッシュ付き）。
2. **サンプリング判定**: ユーザーID等をキーに、Interleaving 対象ユーザーか判定。
3. **ランキング生成**:
    - **A/B**: 既存通りの単一実行。
    - **Interleaving**: A/B 両方のランキングロジックを並行実行。
4. **合成 (Interleaving)**: Team Draft 法などで2つのランキングを合成。
5. **ログ出力**: 各アイテムの出典（A or B）をログに記録。

### 多様なアルゴリズムへの対応 (Ranker Adapter)
A面/B面で全く異なるレコメンドアルゴリズム（例: ルールベース vs 機械学習モデル、あるいは異なる呼び出しI/Fを持つモデル同士）を採用する場合でも、統一的に扱えるよう **Ranker Adapter** パターンを採用します。

- **`Ranker` Interface**: すべてのランキング生成ロジックは共通のインターフェース（例: `rank(context) -> List[Item]`）を実装します。
- **Adapter**: 既存のレガシーコードや異なるシグネチャを持つ関数をラップし、`Ranker` インターフェースに適合させます。
- これにより、Interleaving ロジック側は「Aの詳細は知らず、単にランキングを取得する」だけで済み、アルゴリズムの組み合わせを柔軟に変更可能です。

## 並行処理方針
Python (CPython) の GIL の制約を考慮し、まずは `ThreadPoolExecutor` (max_workers=2) を採用します。
I/O 待ちや、NumPy/ONNX Runtime 等のネイティブコード実行が多い場合、スレッド並行でも十分な高速化が見込めます。
効果が薄い場合は、設定により逐次実行へフォールバック可能な設計とします。

## 設定管理 (SSM)
Layer を使用しないため、アプリ内に設定取得ロジックを含めます。
- `/reco/exp/mode`: 現在のモード (`A`, `B`, `INTERLEAVE`)
- `/reco/exp/sampling_rate`: 適用率
- `/reco/exp/parallel_enabled`: 並行実行の有効化
- `/reco/exp/interleave_method`: アルゴリズム指定
- `/reco/exp/seed_strategy`: シード戦略

## 自動最適化 (Optimized Interleaving)
**Probabilistic Interleaving (Softmax-based)** を実装済みです。
Team Draft (決定論的) との設定切り替えが可能で、オンライン学習によるランキング最適化への道筋をつけています。

1. **Factory Pattern**: `get_interleaver(method)` により、Team Draft と Optimized (Probabilistic) をシームレスに切り替えます。
2. **Probabilistic Selection**: 各アイテムのスコア(ランク由来)に基づき、Softmax確率でソースを選択。選択確率(`prob`)を記録し、不偏推定量(IPS)の計算を可能にします。
3. **Graceful Degradation**: どちらかのアルゴリズムがエラーやタイムアウトを起こした場合でも、自動的に健全な側（またはBaseline）に倒す仕組みと統合します。

## ログ設計
勝敗判定のため、以下の情報をログに追加します。
- `ranking_id`: 1リクエストを一意に識別
- `items`: リスト内の各アイテムに対し `source_ranker` (A または B) を付与
- `mode`: 実行モード
