# Cloud Native Interleaving

## 目的
本プロジェクトの目的は、現行の API Gateway ルーティングによる A/B テストを廃止し、同一 Lambda 呼び出し内で **Interleaving (混ぜ合わせ)** に置換することで、評価速度（統計収束速度）を劇的に改善することです。

## 到達点 (Done)
- **単一エンドポイント**: 設定により `A`, `B`, `Interleaving` を即時切替可能にする。
- **最小改修**: 既存ロジックへの変更を最小限に抑え、ランキング結果を返す直前の「差し込み」で実現する。
- **並行処理**: A/B のランキング生成を同一リクエスト内で並行実行し、レイテンシ悪化を抑える。
- **評価基盤**: ログに「どのアイテムが A/B どちら由来か」を記録し、公正な勝敗集計を可能にする。

## アーキテクチャ

### 現状 (As-Is)
- API Gateway で A/B 別々のルートに振り分け。
- ユーザーは A または B の固定されたロジックの結果のみを受け取る。

### 目標 (To-Be)
- **API Gateway の A/B ルーティングを廃止**。
- Lambda 内部で設定値 (SSM) に基づき、動的に A/B/Interleaving を決定。
- Interleaving 時は A と B の結果を **Team Draft** または **Probabilistic (Optimized)** アルゴリズムで合成して返却。

詳細なアーキテクチャ設計は [docs/architecture.md](docs/architecture.md) を参照してください。

## ドキュメント
- [アーキテクチャ設計](docs/architecture.md)
- [実装・移行計画](docs/implementation_plan.md)
- [リスクと対策](docs/risks_and_mitigation.md)
