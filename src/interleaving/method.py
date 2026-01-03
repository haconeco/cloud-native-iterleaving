
import random
from typing import List, Optional, Set
from src.context import Item

class TeamDraftInterleaver:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def interleave(self, list_a: List[Item], list_b: List[Item]) -> List[Item]:
        """
        Team Draft Interleaving:
        2つのランキングリストから、Team Draft法を用いて新たなランキングを生成する。
        重複アイテムは除外される。
        
        Args:
            list_a: Team A produced items
            list_b: Team B produced items
            
        Returns:
            Interleaved items with `source_ranker` attributed.
        """
        result: List[Item] = []
        used_ids: Set[str] = set()
        
        # Make copies to pop from
        # (Assuming shallow copy is enough as we don't mutate items much)
        # Note: We need to pop from calculation perspective, but list usage with index is better to avoid list mutation issues
        # Or simple queue approach.
        
        queue_a = list(list_a)
        queue_b = list(list_b)
        
        # Team counts (how many items each team successfully placed)
        count_a = 0
        count_b = 0
        
        while queue_a or queue_b:
            if not queue_a and not queue_b:
                break
                
            # Determine which team drafts next
            # If Team A has placed fewer items, it *might* be its turn, 
            # but Team Draft usually implies balancing the opportunity to pick.
            # Simplified Team Draft:
            # - If count_a < count_b: Team A picks
            # - If count_b < count_a: Team B picks
            # - If equal: Randomly decide who picks next (coin flip)
            
            next_team = None
            
            if count_a < count_b:
                next_team = "A"
            elif count_b < count_a:
                next_team = "B"
            else:
                # Equal counts, coin flip
                if self.rng.random() < 0.5:
                    next_team = "A"
                else:
                    next_team = "B"
            
            # Try to pick from the chosen team
            picked_item = None
            source = None
            
            if next_team == "A":
                if queue_a:
                    picked_item = queue_a.pop(0)
                    source = "A"
                elif queue_b:
                    # Fallback to B if A is empty
                    picked_item = queue_b.pop(0)
                    source = "B"
            else: # next_team == "B"
                if queue_b:
                    picked_item = queue_b.pop(0)
                    source = "B"
                elif queue_a:
                    # Fallback to A if B is empty
                    picked_item = queue_a.pop(0)
                    source = "A"
            
            if picked_item:
                if picked_item.id not in used_ids:
                    # New item, add to result
                    picked_item.source_ranker = source
                    result.append(picked_item)
                    used_ids.add(picked_item.id)
                    
                    if source == "A":
                        count_a += 1
                    else:
                        count_b += 1
                else:
                    # Already used (duplicate), just discard and don't increment team count
                    # Because checking "if picked_item.id in used_ids" means this item was already placed by the OTHER team
                    # (or same team earlier if duplicates inside single list, but assuming unique inside single list)
                    # If duplicate, we just consume it. The team technically "used its turn" to pick a duplicate,
                    # but usually in Team Draft, if the top item is already picked, 
                    # the team effectively "skips" that item and picks the next one available?
                    #
                    # Wait, standard implementation:
                    # "If the top item of the team is already in the list, discard it and consider the next item."
                    # We continue the loop.
                    
                    # But if we just 'continue', we need to make sure we don't re-flip the coin if the team hasn't successfully placed an item yet?
                    # Actually, if we discard, `count_a` doesn't increment. So the loop logic `if count_a < count_b` handles it.
                    # It will try to let A pick again.
                    pass
                    
        return result
