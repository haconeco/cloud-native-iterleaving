
import pytest
from typing import List
from src.context import Item
from src.interleaving.method import TeamDraftInterleaver

@pytest.fixture
def items_a():
    return [
        Item(id="a1", score=10),
        Item(id="a2", score=9),
        Item(id="a3", score=8),
    ]

@pytest.fixture
def items_b():
    return [
        Item(id="b1", score=10),
        Item(id="b2", score=9),
        Item(id="b3", score=8),
    ]

def test_team_draft_interleaving_length(items_a, items_b):
    interleaver = TeamDraftInterleaver()
    # 合計6件、Interleaving結果も6件 (重複ない場合)
    result = interleaver.interleave(items_a, items_b)
    assert len(result) == 6

def test_team_draft_attribution(items_a, items_b):
    interleaver = TeamDraftInterleaver()
    result = interleaver.interleave(items_a, items_b)
    
    for item in result:
        assert item.source_ranker in ["A", "B"]
        if item.id.startswith("a"):
            assert item.source_ranker == "A"
        elif item.id.startswith("b"):
            assert item.source_ranker == "B"

def test_team_draft_deduplication():
    # 重複アイテムがある場合
    items_a = [Item(id="common", score=10), Item(id="a2", score=9)]
    items_b = [Item(id="common", score=10), Item(id="b2", score=9)]
    
    interleaver = TeamDraftInterleaver()
    result = interleaver.interleave(items_a, items_b)
    
    # "common" は1つだけ含まれるべき
    ids = [item.id for item in result]
    assert ids.count("common") == 1
    assert len(result) == 3 # common, a2, b2

def test_team_draft_deterministic_with_seed(items_a, items_b):
    # シードを指定した場合、結果が再現すること
    interleaver = TeamDraftInterleaver(seed=42)
    result1 = interleaver.interleave(items_a, items_b)
    
    interleaver2 = TeamDraftInterleaver(seed=42)
    result2 = interleaver2.interleave(items_a, items_b)
    
    ids1 = [item.id for item in result1]
    ids2 = [item.id for item in result2]
    
    assert ids1 == ids2

def test_handling_empty_lists():
    items_a = [Item(id="a1", score=10)]
    items_b = []
    
    interleaver = TeamDraftInterleaver()
    result = interleaver.interleave(items_a, items_b)
    
    assert len(result) == 1
    assert result[0].id == "a1"
