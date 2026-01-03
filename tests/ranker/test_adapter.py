
import pytest
from typing import List, Dict, Any
from src.context import Context, Item
from src.ranker.adapter import LambdaRankerAdapter

# Mock existing logic function
def mock_logic_func(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    # The existing logic is expected to receive a dict and return a list of dicts/objects
    # Here we simulate it returning a list of dicts that need conversion to Items
    user_id = context.get('user_id')
    return [
        {'id': 'item1', 'score': 0.9, 'meta_data': 'foo'},
        {'id': 'item2', 'score': 0.8},
    ]

def test_adapter_converts_context_and_result():
    adapter = LambdaRankerAdapter(logic_func=mock_logic_func)
    
    ctx = Context(user_id="user1", user_hash=123, params={'foo': 'bar'})
    
    # rank method should accept Context object
    items = adapter.rank(ctx)
    
    assert len(items) == 2
    assert isinstance(items[0], Item)
    assert items[0].id == 'item1'
    assert items[0].score == 0.9
    assert items[0].meta == {'meta_data': 'foo'}
    
    assert items[1].id == 'item2'
