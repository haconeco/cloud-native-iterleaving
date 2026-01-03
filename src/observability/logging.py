
import json
import logging
from typing import List, Any
from src.context import Context, Item

logger = logging.getLogger("interleaving")
logger.setLevel(logging.INFO)
# Handler設定はLambda環境等に依存するため、ここでは標準出力への出力のみを想定
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

def log_ranking_result(ranking_id: str, mode: str, context: Context, items: List[Item]):
    """
    ランキング結果を構造化ログ(JSON)として出力する。
    """
    
    log_data = {
        "event": "ranking_generated",
        "ranking_id": ranking_id,
        "mode": mode,
        "user_id": context.user_id,
        "user_hash": context.user_hash,
        "items": [
            {
                "id": item.id,
                "score": item.score,
                "rank": i + 1,
                "source_ranker": item.source_ranker
            }
            for i, item in enumerate(items)
        ]
    }
    
    logger.info(json.dumps(log_data))

