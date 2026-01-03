
from typing import List, Callable, Dict, Any
from src.context import Context, Item
from src.ranker.base import Ranker

class LambdaRankerAdapter(Ranker):
    """
    既存のLambda/関数ベースのランキングロジックをラップし、
    Rankerインターフェースに適合させるアダプター
    """
    def __init__(self, logic_func: Callable[[Dict[str, Any]], List[Dict[str, Any]]]):
        self.logic_func = logic_func

    def rank(self, context: Context) -> List[Item]:
        # Context -> Dict変換 (必要なら)
        # 既存ロジックはdictを受け取ると仮定
        ctx_dict = {
            'user_id': context.user_id,
            'user_hash': context.user_hash,
            **context.params
        }
        
        raw_results = self.logic_func(ctx_dict)
        
        # Raw Dict -> Item変換
        items = []
        for raw in raw_results:
            # 必須フィールドの抽出
            item_id = raw.get('id')
            score = raw.get('score', 0.0)
            
            # その他のパラメーターはmetaに入れる
            meta = {k: v for k, v in raw.items() if k not in ['id', 'score']}
            
            items.append(Item(id=str(item_id), score=float(score), meta=meta))
            
        return items
