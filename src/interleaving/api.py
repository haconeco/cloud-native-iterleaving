
from typing import List, Protocol, Optional, Any
from src.context import Item
from src.interleaving.method import TeamDraftInterleaver, OptimizedInterleaver

class Interleaver(Protocol):
    def interleave(self, list_a: List[Item], list_b: List[Item]) -> List[Item]:
        ...

def get_interleaver(method: str, seed: Optional[int] = None) -> Interleaver:
    """
    Factory function to get the appropriate Interleaver instance.
    
    Args:
        method (str): "team_draft" or "optimized"
        seed (Optional[int]): Random seed for reproducibility
        
    Returns:
        Interleaver: An instance of a class implementing interleave method.
    """
    if method == "optimized":
        return OptimizedInterleaver(seed=seed)
    else:
        # Default or "team_draft"
        return TeamDraftInterleaver(seed=seed)
