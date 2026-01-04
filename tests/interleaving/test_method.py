
import pytest
from typing import List
from src.context import Item
from src.interleaving.method import TeamDraftInterleaver, OptimizedInterleaver

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

def test_optimized_interleaving_basic(items_a, items_b):
    interleaver = OptimizedInterleaver()
    result = interleaver.interleave(items_a, items_b)
    
    assert len(result) == 6
    for item in result:
        assert item.source_ranker in ["A", "B"]
        assert item.prob is not None
        assert 0.0 <= item.prob <= 1.0

def test_optimized_interleaving_distribution(items_a, items_b):
    # A1(rank0) vs B1(rank0) -> scores equal -> prob should be 0.5
    interleaver = OptimizedInterleaver(tau=1.0)
    
    # Check probability calculation logic (whitebox-ish or blackbox via prob field)
    # We can check the recorded probability in the result.
    # Note: this depends on which was picked.
    # If A1 picked, prob should be P(A). If B1 picked, prob should be P(B).
    # Since scores are equal, both should be 0.5
    
    # But prob recording might be P(selected).
    
    result = interleaver.interleave(items_a, items_b)
    first_item = result[0]
    # For equal rank items at top, prob should be ~0.5
    assert 0.49 < first_item.prob < 0.51

def test_optimized_interleaving_deduplication():
    items_a = [Item(id="common", score=10), Item(id="a2", score=9)]
    items_b = [Item(id="common", score=10), Item(id="b2", score=9)]
    
    interleaver = OptimizedInterleaver()
    result = interleaver.interleave(items_a, items_b)
    
    assert len(result) == 3
    ids = [item.id for item in result]
    assert ids.count("common") == 1

