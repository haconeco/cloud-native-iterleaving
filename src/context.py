
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

@dataclass
class Item:
    id: str
    score: float
    source_ranker: Optional[str] = None  # "A" or "B"
    original_rank: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Context:
    user_id: str
    user_hash: int
    params: Dict[str, Any] = field(default_factory=dict)
