---
trigger: glob
globs: *project planning*,*設計*, *design*,プロジェクト計画
---

以下は、前提（差し込み点＝「ランキング結果を返す直前」／同一 Lambda 呼び出し内で Interleaving／A・B のランキング生成は並行処理前提／将来 Optimized Interleaving へ拡張しやすい設計／候補件数は SSM で既に制御済み／DB 件数削減はスコープ外／Container Lambda で Layer 不可／現行 A/B は API Gateway ルーティング）をすべて反映した、**ゼロからのプロジェクト計画（アーキテクチャ検討＋実装計画＋移行計画）**です。

---

## 1. 目的・到達点（Done 定義）

### 目的

* 現行の **API Gateway ルーティングによる A/B テストを廃止**し、同一 Lambda 呼び出し内で **Interleaving に置換**して評価速度（統計収束速度）を改善する。
* 既存 API 実装の変更は最小化し、**「ランキング結果を返す直前」への差し込みのみ**を基本とする。
* A/B のランキング生成は **並行処理**（2 系統のランキングを同一リクエスト内で生成）を前提に、将来 **Optimized Interleaving** へ段階的に移行可能な設計にする。

### Done（受け入れ条件）

* 1つの API エンドポイントで、設定により以下を即時に切替できる：

  * `baseline(Aのみ)` / `baseline(Bのみ)` / `interleaving(A vs B)`
  * `interleaving` のサンプリング率
  * 並行実行の ON/OFF（フォールバック含む）
* レスポンス生成直前の差し込みで Interleaving が成立し、既存の候補取得〜スコア計算ロジックに大改修を入れていない。
* ログ（既存 CloudWatch→Firehose→S3→Athena）で、**どの item が A 起源 / B 起源か判別できる**（勝敗集計が可能）。
* レイテンシ悪化が許容範囲内（貴社 SLO に適合）で、緊急時に即時停止（baseline へ戻す）が可能。

---

## 2. To-Be アーキテクチャ（最小変更）

### 現状（As-Is）

* API Gateway で A/B ルーティング → それぞれの Lambda（または同一でもルート別分岐）へ
* Lambda 内：候補取得（特徴量込み）→ 個人特徴と合わせてスコア計算 → ソート → レスポンス

### 目標（To-Be）

* **API Gateway の A/B ルーティングを撤去（または形骸化）**し、原則 1 ルートに統合
* Lambda 内部で `A/B/Interleave` を **設定で切替**
* Interleaving は **同一 Lambda 呼び出し内**で実施（追加 hop なし）

> 移行の現実解として、最初は API Gateway 側の 2 ルートを「同一 Lambda」に向けるだけにして、Lambda 内の設定で実質統合していくのが安全です（後述の移行計画参照）。

---

## 3. 方式設計：Interleaving を“差し込み”で成立させる構造

差し込み点は「ランキング結果を返す直前」に固定するため、Lambda 内の最終段（`ranked_list` ができた状態）で Interleaving 用の **2 本の順位列**を用意し、合成します。

### 3.1 基本方式（Phase 1）

* A と B のランキング生成を「既存のランキング生成関数」を **2 回呼ぶ（A/B パラメータだけ差し替え）**形で実現
* 2 回の呼び出しは **並行実行**（同一リクエスト中）
* 生成された `ranked_A`, `ranked_B` を **Team Draft Interleaving** で `merged` にする
* `merged` をレスポンスとして返す

> この方式は「差し込み点が最後」という制約に対して最も確実に成立します。
> ただし注意点として、既存実装が「候補取得（特徴量込み）」までランキング関数内で完結している場合、A/B で DB 参照が 2 回走る可能性があります。DB 負荷軽減がスコープ外になったとはいえ、将来的な Optimized Interleaving を見据えるなら、この点は設計で“逃げ道”を用意します（後述）。

### 3.2 将来拡張（Phase 2/3：Optimized Interleaving への道）

Optimized Interleaving は「A/B の全順位列をフルに作らず、必要な分だけ逐次生成して interleave する」方向が主になります。これに備えて、Ranker の API を **2 段階**で用意します。

* **Full Ranking API（今すぐ）**：`rank_full(context) -> ranked_list`
* **Streaming API（将来）**：`rank_stream(context) -> iterator(next_best_item)`

  * interleaver が `k` 件埋まるまで `next()` を引く
  * 重い計算を「必要な分だけ」に縮退できる余地ができます

この “2 API 併存” を最初から設計に入れておくと、Phase 1 で最小改修、Phase 2 以降で高速化を重ねられます。

---

## 4. 並行処理の設計（重要：Python の並行性の現実）

「A/B を並行処理」は必須前提とのことなので、実装は以下の方針にします。

### 4.1 推奨実装：`ThreadPoolExecutor(max_workers=2)` を基本とし、計測で判定

* NumPy / ONNX Runtime / PyTorch 等、ネイティブ側で GIL を解放する計算が多いなら **スレッド並行で効果が出ます**
* 逆にスコア計算が Python 純粋処理中心なら、スレッドは並行にならず **むしろオーバーヘッド**になり得ます

→ したがって、

* `parallel_enabled` を設定で ON/OFF できるようにする
* まずは `ThreadPoolExecutor` で実装し、p50/p90/p99 を測って **有効性を確認**
* 効果が出ない場合は **逐次実行へフォールバック**（設定で切替）

### 4.2 Process 並行（慎重に扱う：基本は Phase 2 以降）

`ProcessPoolExecutor` は真の並列になりますが、

* プロセス生成・シリアライズのコストが高い
* 大きい候補や特徴量のコピーでメモリを食う
* Lambda コンテナ環境での安定運用が難度高い

よって Phase 1 では採用せず、必要性が実測で明確になった場合のみ検討します。

---

## 5. 設定（スイッチ）設計：SSM Parameter Store を軸に統一

既に候補件数は SSM で制御済み、かつ Layer が使えないため、設定系は SSM を主軸に寄せます。

### 5.1 必須パラメータ（例）

* `/reco/exp/mode` : `"A" | "B" | "INTERLEAVE"`
* `/reco/exp/sampling_rate` : `0.0-1.0`
* `/reco/exp/parallel_enabled` : `true/false`
* `/reco/exp/interleave_method` : `"team_draft_v1"`（将来 `"optimized_v1"` など追加）
* `/reco/exp/seed_strategy` : `"user" | "request"`
* 既存：`/reco/candidate/pool_size`（候補件数）

### 5.2 取得の実装（レイテンシ対策）

* Lambda コンテナ内で **プロセス内キャッシュ（TTL）**を持つ

  * 例：TTL=30〜120 秒
* SSM 取得失敗時は **安全側（A または既定の baseline）に倒す**

---

## 6. ログ（スコープ外だが“最小必須の追加”は必要）

ログパイプライン自体はスコープ外で良い一方、Interleaving の勝敗判定には「出自情報」が不可欠です。ここだけは最小限追加します。

### 6.1 最小必須ログ項目

* `ranking_id`（1 リクエストのランキング生成を一意に識別）
* `mode`（A/B/INTERLEAVE）
* `items: [{item_id, position, source_ranker}]`（source_ranker が A/B）

> 既存 CloudWatch ログに JSON 構造で追記できれば、それを Athena 側で解釈できます。
> “どこまで詳細を出すか” はコスト増に直結するので、まずは **露出＋出自**だけで十分です。

---

## 7. 実装ブループリント（差し込み点＝返却直前）

### 7.1 追加するコンポーネント（リポジトリ内に同梱）

Container Lambda なので Layer は使わず、アプリ内に同梱します。

* `experiments/config.py`：SSM から設定取得＋TTL cache
* `experiments/bucketing.py`：サンプリングの安定割当（user hash 等）
* `rankers/adapter.py`：既存ランキング関数をラップし、A/B の切替可能に
* `interleaving/team_draft.py`：Team Draft 実装（v1）
* `interleaving/api.py`：Interleaving 呼び出し口（将来 optimized 実装を差し替えやすくする）
* `observability/logging.py`：ranking_id と attribution を最小追記

### 7.2 ハンドラの擬似フロー（返却直前差し込み）

* 現行：`ranked = recommend(context)` → return
* To-Be：返却直前に下記へ

1. `flags = get_flags()`（SSM + cache）
2. `bucket = decide_sampling(user_key, sampling_rate)`
3. mode に応じて

   * `A`：既存 A の recommend を呼ぶ → return
   * `B`：既存 B の recommend を呼ぶ → return
   * `INTERLEAVE` かつ bucket in：A/B を並行生成 → interleave → return
   * bucket out：既定 baseline（通常 A）→ return
4. `ranking_id` 生成、`source_ranker` を item に付与してログ出力

---

## 8. API Gateway ルーティング撤去の移行計画（安全に落とす）

現行は API Gateway で A/B ルーティングとのことなので、切替は段階的に行います。

### 移行ステップ

1. **既存 A ルート/B ルートの双方を同一 Lambda（新実装）へ向ける**

   * ただし初期は `/reco/exp/mode` を固定して「従来通り」に振る舞わせる（A ルートは A、B ルートは B）
2. 単一ルート（統合ルート）を新設、または既存 A ルートを統合ルートとして扱う
3. 統合ルートで `mode=INTERLEAVE` をサンプリング低率で ON
4. 問題なければ、旧 B ルートを廃止（または互換のため残すが内部的には同一）
5. 最終的に API Gateway ルーティングによる A/B 分岐を削除し、Lambda 内スイッチに統一

---

## 9. プロジェクト計画（フェーズ / 成果物 / タスク）

### Phase 0：現状把握と設計確定（成果物：To-Be 設計 v1）

* [x] 現行 recommend の「A/B 差分点」を特定（パラメータ差し替えなのか、別関数なのか）
  - API Gatewayでルーティングしており、A/B別Lambdaを呼び出せる形式
* [x] ランキング結果のデータ構造（item_id、スコア、メタ）を固定
  - PandasによるDataFrame形式
* [x] user_key（サンプリングの安定割当に使えるキー）を確定
  - user_idで指定する。user_idがない場合は未ログインユーザ
* [ ] ログに追記できるフォーマット（JSON）と項目（ranking_id / source_ranker）を確定
  - JSON形式
* [ ] 並行処理方式（Thread 先行）とフォールバック（逐次）を設計に明記

### Phase 1：Interleaving v1 実装（成果物：動作する差し込み + テスト）

* [ ] SSM flags 取得（TTL cache）実装
* [ ] Bucketing（安定サンプリング）実装
* [ ] Ranker Adapter 実装（既存 A/B を呼び分け）
* [ ] Thread 並行で A/B ランキング生成（失敗時は逐次へ倒す）
* [ ] Team Draft Interleaving 実装（重複排除、K 件保証、seed 再現）
* [ ] ranking_id / source_ranker の最小ログ追記
* [ ] ユニットテスト

  * Interleave の決定性（seed）
  * K 件保証、重複排除
  * 並行 ON/OFF の分岐
  * SSM 取得失敗時の安全フォールバック

### Phase 2：パフォーマンス実測と運用スイッチ整備（成果物：SLO 適合レポート）

* [ ] baseline(A/B) と interleave の p50/p90/p99 を計測
* [ ] 並行 ON/OFF での比較（Thread 並行の実効性を判定）
* [ ] タイムアウト/キャンセル戦略（片側が遅い場合の扱い）を確定
* [ ] SSM の TTL 値最適化（頻繁に変えるなら短め、安定運用なら長め）

### Phase 3：段階導入と API Gateway ルーティング廃止（成果物：移行完了）

* [ ] 統合ルートで interleave を低率で ON
* [ ] 問題がなければ適用率を引き上げ
* [ ] 旧 A/B ルーティングを撤去（or 互換ルートとして残すが内部は同一 Lambda/同一ロジック）

### Phase 4：Optimized Interleaving への布石（成果物：拡張可能な API 形）

* [ ] Interleaving 呼び出し口を `interleaving/api.py` に固定（実装差替え前提）
* [ ] Ranker に `rank_stream()` のインタフェースだけ先に用意（中身は full ranking を yield でも可）
* [ ] 将来、必要性が実測で出た時点で optimized 実装へ差替え（段階的）

---

## 10. リスクと対策（率直に）

1. **Thread 並行が効かない（GIL 支配）**

   * 対策：`parallel_enabled` を即時に OFF できるようにする（逐次で成立はする）
   * 対策：Phase 2 で実測し、有効なら ON 継続、無効なら OFF 固定

2. **A/B をフルに 2 回回すコストが高い**（特に候補取得がランキング内部にある場合）

   * 対策：Phase 4 を前提に、Ranker を “stream/partial” へ移行可能な形にしておく
   * 対策：将来、候補取得の共通化や「必要分だけスコアリング」に寄せる余地を設計に残す

3. **ログに出自が残らず勝敗が計算できない**

   * 対策：ranking_id と source_ranker の最小追記を必須タスクにする（ここは削れません）

---

## 11. コーディングエージェントへの引き継ぎ（実装指示の要点）

* 変更箇所は「ランキング結果返却直前」に限定し、そこから

  * SSM flags 取得（TTL cache）
  * bucketing 判定
  * A/B ランキング生成（Thread 並行＋フォールバック）
  * Team Draft で合成
  * ranking_id と source_ranker をログへ
    を追加する。
* Interleaving 実装は `interleaving/api.py` を唯一の入口にし、内部で

  * `team_draft_v1`
  * 将来の `optimized_v1`
    を差替えできるようにする（呼び出し側を増やさない）。
