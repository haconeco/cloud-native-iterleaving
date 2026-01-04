
import pytest
from src.interleaving.api import get_interleaver
from src.interleaving.method import TeamDraftInterleaver, OptimizedInterleaver

def test_get_team_draft():
    interleaver = get_interleaver("team_draft")
    assert isinstance(interleaver, TeamDraftInterleaver)

def test_get_optimized():
    interleaver = get_interleaver("optimized")
    assert isinstance(interleaver, OptimizedInterleaver)

def test_get_default():
    # Unknown method should result in default (Team Draft)
    interleaver = get_interleaver("unknown_method")
    assert isinstance(interleaver, TeamDraftInterleaver)

def test_get_interleaver_with_seed():
    interleaver = get_interleaver("team_draft", seed=123)
    assert interleaver.rng.randint(0, 100) == 6  # Deterministic check depends on impl, but at least object exists
    assert isinstance(interleaver, TeamDraftInterleaver)
