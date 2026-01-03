# 詳細設計書: Interleaving v1 (Library)

## 1. モジュール構成とディレクトリ構造

本リポジトリは **ライブラリ** として機能し、利用側のメインハンドラから呼び出されることを想定しています。

```text
.
├── src/
│   ├── config.py           # 設定管理 (SSM / Env)
│   ├── context.py          # コンテキスト (Request Scope data)
│   ├── interleaving/
│   │   ├── bucketer.py     # ユーザーハッシュとサンプリング
│   │   └── method.py       # Team Draft などのアルゴリズム詳細
│   ├── ranker/
│   │   ├── base.py         # Ranker Interface
│   │   └── adapter.py      # 既存ロジックへの Adapter
│   └── logger.py           # 構造化ログ出力
└── tests/
    ├── test_config.py
    ├── interleaving/
    │   ├── test_bucketer.py
    │   └── test_method.py
    └── ranker/
        └── test_adapter.py
```

## 2. クラス設計

### 2.1. ConfigManager (`src/config.py`)
実験の設定を管理します。SSM Parameter Store からの値の取得と、TTLによるキャッシュを担当します。

```python
@dataclass
class ExperimentConfig:
    mode: str  # "A", "B", "INTERLEAVE"
    sampling_rate: float
    parallel_enabled: bool = True

class ConfigManager:
    def get_config(self) -> ExperimentConfig:
        # SSM から取得、キャッシュにあればそれを返す
        pass
```

### 2.2. Bucketer (`src/interleaving/bucketer.py`)
外部で計算済みのユーザーハッシュ値を受け取り、サンプリング率に基づいてユーザーが実験対象か（Interleaving対象か）を判定します。

```python
class Bucketer:
    def determine_mode(self, user_hash: int, config: ExperimentConfig) -> str:
        # user_hash (int) をそのまま利用
        # sampling_rate 内であれば config.mode を返す (例: "INTERLEAVE")
        # 対象外であればデフォルト ("A" or "B") を返す
        pass
```

### 2.3. Ranker Interface & Adapter (`src/ranker/`)
異なるランキングロジックを統一的に扱うためのインターフェースです。

```python
# src/ranker/base.py
class Ranker(Protocol):
    def rank(self, context: dict) -> List[Item]:
        ...

# src/ranker/adapter.py
class LambdaRankerAdapter(Ranker):
    def __init__(self, logic_func):
        self.logic_func = logic_func

    def rank(self, context: dict) -> List[Item]:
        # 既存ロジック呼び出し
        return self.logic_func(context)
```

### 2.4. Interleaver (`src/interleaving/method.py`)
2つのランキングリストを合成します。初期実装では **Team Draft Interleaving** を採用します。

```python
class TeamDraftInterleaver:
    def interleave(self, list_a: List[Item], list_b: List[Item]) -> List[Item]:
        # Team Draft アルゴリズムの実装
        # 結果のアイテムには `source_ranker` ("A" or "B") を付与
        pass
```

## 3. データ構造

### Item
ランキングの要素です。

```python
@dataclass
class Item:
    id: str
    score: float
    source_ranker: Optional[str] = None  # "A" or "B" (Interleaving後のみ設定)
    original_rank: Optional[int] = None
```

## 4. 利用イメージ (Sample Handler)

本ライブラリを利用する側の実装イメージです（`tests/sample_handler.py` として実装予定）。

1. **Request受信**: ユーザーID等のコンテキスト抽出。**ユーザーハッシュ値もここで取得/計算済み**とする。
2. **Config取得**: `ConfigManager.get_config()`
3. **Mode判定**: `Bucketer.determine_mode(user_hash, config)`
4. **ランキング生成**:
    - **Interleave Mode**:
        - `ThreadPoolExecutor` で `ranker_a.rank()` と `ranker_b.rank()` を並行実行
        - `TeamDraftInterleaver.interleave(res_a, res_b)` を実行
    - **A/B Mode**:
        - 対応する `ranker.rank()` を実行
5. **Response返却 & ログ出力**

## 5. テスト戦略
t_wada 推奨の TDD サイクルに従い実装します。

1. **Test**: 各コンポーネントの期待する振る舞いをテストコードとして記述（Red）。
2. **Code**: テストを通すための最小限の実装（Green）。
3. **Refactor**: 設計に基づきコードを整理（Refactor）。

特に `TeamDraftInterleaver` はロジックが複雑になりがちなので、詳細なユニットテストケースを用意します（空リスト、長さ違い、重複など）。
また、結合動作確認として `tests/sample_handler.py` を用いた動作検証を行います。
