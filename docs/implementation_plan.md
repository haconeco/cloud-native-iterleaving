# 実装・移行計画

## フェーズ分け

### Phase 0: 現状把握と設計確定
- アーキテクチャ設計、ログフォーマット、並行処理方針の策定。
- **(完了)** プロジェクト計画書作成。

### Phase 1: Interleaving v1 実装
- **SSM連携**: 設定取得とキャッシュ機作の実装。
- **Bucketing**: ユーザーハッシュによる安定したサンプリング実装。
- **Ranker Adapter**: 既存ランキング関数をラップし、A/B パラメータで呼び分け可能に。
- **Interleaving Logic**: Team Draft Interleaving の実装。
- **並行実行**: ThreadPoolExecutor による A/B 並列化。
- **ログ**: 出自情報 (`source_ranker`) の出力。

### Phase 2: パフォーマンス実測と運用スイッチ整備
- レイテンシ計測 (p50/p90/p99)。
- Thread 並行の効果検証と、必要に応じたチューニング。
- タイムアウト戦略の確定。
- SSM TTL設定の最適化。

### Phase 3: 段階導入と API Gateway ルーティング廃止
- 新 Lambda (Interleaving 対応版) へのトラフィック移行。
- 当初は `mode=A` / `mode=B` で既存挙動を再現。
- 徐々に `mode=INTERLEAVE` を有効化。
- 最終的に API Gateway の A/B 分岐設定を削除。

### Phase 4: 将来拡張 (Optimized Interleaving)
- 全件ランキング生成を行わず、必要な分だけ逐次生成する "Streaming Ranker" への対応準備。
