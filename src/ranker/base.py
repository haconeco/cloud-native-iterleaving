
from typing import List, Protocol
from src.context import Context, Item

class Ranker(Protocol):
    def rank(self, context: Context) -> List[Item]:
        """
        Contextを受け取り、ランキング生成（Itemのリスト）を返す
        """
        ...
