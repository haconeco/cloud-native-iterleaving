
import pytest
from src.config import ExperimentConfig
from src.interleaving.bucketer import Bucketer

@pytest.fixture
def config_interleave():
    return ExperimentConfig(
        mode="INTERLEAVE",
        sampling_rate=0.5,
        parallel_enabled=True
    )

def test_bucketer_determines_mode_in_sample(config_interleave):
    bucketer = Bucketer()
    # 50% sampling, use hash that yields < 0.5
    # (1 % 10000) / 10000 = 0.0001 < 0.5
    assert bucketer.determine_mode(user_hash=1, config=config_interleave) == "INTERLEAVE"

def test_bucketer_determines_mode_out_sample(config_interleave):
    bucketer = Bucketer()
    # 50% sampling, use hash that yields >= 0.5
    # (6000 % 10000) / 10000 = 0.6 >= 0.5
    assert bucketer.determine_mode(user_hash=6000, config=config_interleave) != "INTERLEAVE"
    # Default fallback assumes "A" (or whatever logic defined)
    assert bucketer.determine_mode(user_hash=6000, config=config_interleave) == "A"

def test_bucketer_handles_config_mode_off(config_interleave):
    config_interleave.mode = "A" # Even if sampling rate is high
    bucketer = Bucketer()
    assert bucketer.determine_mode(user_hash=1, config=config_interleave) == "A"

def test_bucketer_handles_zero_sampling():
    config = ExperimentConfig(mode="INTERLEAVE", sampling_rate=0.0, parallel_enabled=True)
    bucketer = Bucketer()
    assert bucketer.determine_mode(user_hash=0, config=config) == "A"

def test_bucketer_handles_full_sampling():
    config = ExperimentConfig(mode="INTERLEAVE", sampling_rate=1.0, parallel_enabled=True)
    bucketer = Bucketer()
    assert bucketer.determine_mode(user_hash=9999, config=config) == "INTERLEAVE"
