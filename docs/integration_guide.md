# インテグレーションガイド

本ライブラリ `cloud-native-interleaving` を実際のアプリケーション（AWS Lambda 等）に組み込む際の手順書です。

## 1. インストール

`pip` または `requirements.txt` を用いてインストールしてください。

```bash
pip install cloud-native-interleaving
```

または、`src/` ディレクトリを Lambda 関数パッケージに直接コピーして配置することも可能です。

## 2. AWS SSM Parameter Store 設定

本ライブラリは初期化時に AWS SSM Parameter Store から実験設定を取得します。以下のパスにパラメータを設定してください。

| パス | 型 | 値の例 | 説明 |
|---|---|---|---|
| `/reco/exp/mode` | String | `INTERLEAVE`, `A`, `B` | 動作モード。`A` は既存ロジックAのみ、`INTERLEAVE` は並行実行+合成。 |
| `/reco/exp/sampling_rate` | String | `0.0` - `1.0` | INTERLEAVE モードの適用率。`0.1` で 10% のユーザーに適用。 |
| `/reco/exp/parallel_enabled` | String | `true` or `false` | A/B ロジックの並行実行を行うかどうか。 |

> **Note:** 適切な IAM 権限 (`ssm:GetParameters`) が Lambda 実行ロールに付与されていることを確認してください。

## 3. アプリケーション要件

### ユーザーハッシュ (Context)
本ライブラリは、サンプリングの安定性（同じユーザーには常に同じモードを適用する）を保証するために、**ユーザーIDに基づくハッシュ値 (int)** を外部から受け取る設計になっています。

アプリケーション側で以下のようにハッシュ値を計算してください（推奨）。

```python
import mmh3

def get_user_hash(user_id: str) -> int:
    # 符号なし32bit整数として取得することを推奨
    return mmh3.hash(user_id, signed=False)
```

## 4. 実装例

`ranker_a` (既存ロジックA) と `ranker_b` (既存ロジックB) を受け取り、Interleaving された結果を返すハンドラの実装例です。

```python
from src.config import ConfigManager
from src.context import Context
from src.interleaving.bucketer import Bucketer
from src.interleaving.method import TeamDraftInterleaver
from src.ranker.adapter import LambdaRankerAdapter
from src.observability.logging import log_ranking_result
import concurrent.futures
import uuid

# ConfigManagerはハンドラ外で初期化（キャッシュ有効化のため）
config_manager = ConfigManager(ttl_seconds=60.0)
bucketer = Bucketer()
interleaver = TeamDraftInterleaver()

def lambda_handler(event, context):
    user_id = event.get('user_id')
    user_hash = event.get('user_hash') # または内部で計算
    
    # 1. 設定取得
    config = config_manager.get_config()
    
    # 2. モード判定
    mode = bucketer.determine_mode(user_hash, config)
    
    # 3. Context作成
    ctx = Context(user_id=user_id, user_hash=user_hash, params=event)
    
    items = []
    
    # Adapter準備 (ロジック関数をラップ)
    adapter_a = LambdaRankerAdapter(existing_logic_a)
    adapter_b = LambdaRankerAdapter(existing_logic_b)
    
    if mode == "INTERLEAVE":
        # 4. 並行実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(adapter_a.rank, ctx)
            future_b = executor.submit(adapter_b.rank, ctx)
            list_a = future_a.result()
            list_b = future_b.result()
            
        # 5. 合成
        items = interleaver.interleave(list_a, list_b)
        
    elif mode == "B":
        items = adapter_b.rank(ctx)
    else:
        # Default to A
        items = adapter_a.rank(ctx)
        
    # 6. ログ出力 (CloudWatch Logs -> Firehose -> S3 -> Athena)
    ranking_id = str(uuid.uuid4())
    log_ranking_result(ranking_id, mode, ctx, items)
    
    # レスポンス形式に合わせて整形して返却
    return {
        "ranking_id": ranking_id,
        "items": [item.__dict__ for item in items]
    }
```
