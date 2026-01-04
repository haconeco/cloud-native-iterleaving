
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

class OptimizedInterleaver:
    def __init__(self, tau: float = 3.0, seed: Optional[int] = None):
        self.tau = tau
        self.rng = random.Random(seed)

    def interleave(self, list_a: List[Item], list_b: List[Item]) -> List[Item]:
        """
        Optimized Interleaving (Softmax-based):
        Uses softmax function on rank-based scores to probabilistically select
        from list A or list B.
        
        Score = 1 / (rank + 1)^tau
        P(A) = exp(Score_A) / (exp(Score_A) + exp(Score_B))
        """
        import math
        
        result: List[Item] = []
        used_ids: Set[str] = set()
        
        idx_a = 0
        idx_b = 0
        
        len_a = len(list_a)
        len_b = len(list_b)
        
        while idx_a < len_a or idx_b < len_b:
            # Advance pointers to find next available items
            while idx_a < len_a and list_a[idx_a].id in used_ids:
                idx_a += 1
            
            while idx_b < len_b and list_b[idx_b].id in used_ids:
                idx_b += 1
            
            cand_a = list_a[idx_a] if idx_a < len_a else None
            cand_b = list_b[idx_b] if idx_b < len_b else None
            
            if cand_a is None and cand_b is None:
                break
            
            selected_item = None
            prob_a = 0.0
            source = ""
            
            if cand_a and cand_b:
                # Both available, use Softmax
                score_a = 1.0 / ((idx_a + 1) ** self.tau)
                score_b = 1.0 / ((idx_b + 1) ** self.tau)
                
                denom = math.exp(score_a) + math.exp(score_b)
                prob_a = math.exp(score_a) / denom
                
                if self.rng.random() < prob_a:
                    selected_item = cand_a
                    source = "A"
                    # item probability is P(A)
                    selected_item.prob = prob_a
                else:
                    selected_item = cand_b
                    source = "B"
                    # item probability is P(B) = 1 - P(A)
                    selected_item.prob = 1.0 - prob_a
                    
            elif cand_a:
                # Only A available
                selected_item = cand_a
                source = "A"
                selected_item.prob = 1.0
            else:
                # Only B available
                selected_item = cand_b
                source = "B"
                selected_item.prob = 1.0
            
            if selected_item:
                selected_item.source_ranker = source
                result.append(selected_item)
                used_ids.add(selected_item.id)
                # Note: We don't manually increment index here because the loop structure 
                # will skip used IDs in the next iteration's "Advance pointers" phase.
                # BUT, if we don't increment, we will check the same ID again as "in used_ids".
                # It's better to increment the one we picked to save one check, but not strictly required.
                # However, for clarity and avoiding infinite loop if logic is wrong:
                if source == "A":
                    idx_a += 1
                else:
                    idx_b += 1
        
        return result
