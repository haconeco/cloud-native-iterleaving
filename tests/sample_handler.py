
import uuid
import concurrent.futures
from unittest.mock import MagicMock, patch

from src.config import ConfigManager, ExperimentConfig
from src.context import Context, Item
from src.interleaving.bucketer import Bucketer
from src.interleaving.method import TeamDraftInterleaver
from src.ranker.adapter import LambdaRankerAdapter
from src.observability.logging import log_ranking_result

# Mock logic functions (Legacy A/B)
def logic_a(ctx: dict):
    # Retrieve user_id to simulate personalized logic
    return [
        {'id': 'A1', 'score': 10.0, 'algo': 'a'},
        {'id': 'A2', 'score': 9.0, 'algo': 'a'},
        {'id': 'A3', 'score': 8.0, 'algo': 'a'},
        {'id': 'Common', 'score': 7.0, 'algo': 'a'},
    ]

def logic_b(ctx: dict):
    return [
        {'id': 'B1', 'score': 10.0, 'algo': 'b'},
        {'id': 'Common', 'score': 9.5, 'algo': 'b'}, # Common item, higher score in B
        {'id': 'B2', 'score': 9.0, 'algo': 'b'},
    ]

def sample_handler(user_id: str, user_hash: int):
    print(f"--- Handling Request: user_id={user_id}, hash={user_hash} ---")
    
    # 1. Config (In real usage, this fetches from SSM)
    # Patching boto3 to avoid NoRegionError during ConfigManager init
    with patch('src.config.boto3.client') as mock_boto:
        config_manager = ConfigManager()
        # Mocking internals for demo to force INTERLEAVE mode
        config_manager._fetch_from_ssm = MagicMock(return_value=ExperimentConfig(
            mode="INTERLEAVE",
            sampling_rate=0.5, # 50%
            parallel_enabled=True
        ))
        
        config = config_manager.get_config()
        print(f"Config Loaded: mode={config.mode}, rate={config.sampling_rate}, parallel={config.parallel_enabled}")

    # 2. Bucketing
    bucketer = Bucketer()
    mode = bucketer.determine_mode(user_hash, config)
    print(f"Determined Mode: {mode}")
    
    # 3. Context Construction
    ctx = Context(user_id=user_id, user_hash=user_hash)
    
    # 4. Ranking
    # Prepare Rankers
    ranker_a = LambdaRankerAdapter(logic_a)
    ranker_b = LambdaRankerAdapter(logic_b)
    
    items = []
    
    if mode == "INTERLEAVE":
        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(ranker_a.rank, ctx)
            future_b = executor.submit(ranker_b.rank, ctx)
            
            list_a = future_a.result()
            list_b = future_b.result()
            
        print(f"Ranker A returned {len(list_a)} items")
        print(f"Ranker B returned {len(list_b)} items")
        
        # Interleaving
        interleaver = TeamDraftInterleaver(seed=user_hash) # Use user_hash as seed for consistency
        items = interleaver.interleave(list_a, list_b)
        
        # Display simplified result
        display_res = [f"{item.id}({item.source_ranker})" for item in items]
        print(f"Interleaved Result: {display_res}")
        
    elif mode == "A":
        items = ranker_a.rank(ctx)
        print(f"Result (A): {[item.id for item in items]}")
    elif mode == "B":
        items = ranker_b.rank(ctx)
        print(f"Result (B): {[item.id for item in items]}")
    else:
        # Fallback
        items = ranker_a.rank(ctx)
        print(f"Result (Fallback): {[item.id for item in items]}")
        
    # 5. Logging
    ranking_id = str(uuid.uuid4())
    log_ranking_result(ranking_id, mode, ctx, items)
    
    return items

if __name__ == "__main__":
    # Case 1: In Sample (hash=1 -> 0.0001 < 0.5)
    print("Test Case 1: In Sample")
    sample_handler("user_in", 1)
    
    print("\n")
    
    # Case 2: Out Sample (hash=6000 -> 0.6 >= 0.5)
    print("Test Case 2: Out Sample")
    sample_handler("user_out", 6000)
