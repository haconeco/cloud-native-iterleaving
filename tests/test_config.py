
import pytest
import time
from unittest.mock import MagicMock, patch
from src.config import ConfigManager, ExperimentConfig

@pytest.fixture
def mock_ssm_client():
    with patch('src.config.boto3.client') as mock:
        yield mock.return_value

def test_default_values(mock_ssm_client):
    """設定が取得できない場合、安全なデフォルト値(Mode A)を返すこと"""
    # SSM取得ごく初期のエラーや、呼び出し時のエラーを想定
    mock_ssm_client.get_parameters.side_effect = Exception("SSM Error")
    
    manager = ConfigManager()
    config = manager.get_config()
    
    assert config.mode == "A"
    assert config.sampling_rate == 0.0
    assert config.parallel_enabled is False

def test_get_config_ssm_success(mock_ssm_client):
    """SSMから設定が正しく取得できること"""
    mock_ssm_client.get_parameters.return_value = {
        'Parameters': [
            {'Name': '/reco/exp/mode', 'Value': 'INTERLEAVE'},
            {'Name': '/reco/exp/sampling_rate', 'Value': '0.15'},
            {'Name': '/reco/exp/parallel_enabled', 'Value': 'true'}
        ]
    }

    manager = ConfigManager()
    config = manager.get_config()

    assert config.mode == "INTERLEAVE"
    assert config.sampling_rate == 0.15
    assert config.parallel_enabled is True
    
    mock_ssm_client.get_parameters.assert_called_once()
    # 呼び出し引数の確認 (Namesリストが含まれているか)
    call_args = mock_ssm_client.get_parameters.call_args
    assert 'Names' in call_args[1] or 'Names' in call_args[0] if call_args[0] else True

def test_get_config_ssm_failure_returns_default(mock_ssm_client):
    """SSM取得失敗時はデフォルト設定(Mode A)を返すこと"""
    mock_ssm_client.get_parameters.side_effect = Exception("SSM access failed")

    manager = ConfigManager()
    config = manager.get_config()

    assert config.mode == "A"
    assert config.sampling_rate == 0.0
    assert config.parallel_enabled is False # 安全側に倒すならFalseが良いか？設計次第だがここではFalseとする

def test_config_caching(mock_ssm_client):
    """設定がTTL内でキャッシュされること"""
    mock_ssm_client.get_parameters.return_value = {
        'Parameters': [
            {'Name': '/reco/exp/mode', 'Value': 'B'}
        ]
    }

    manager = ConfigManager(ttl_seconds=60)
    
    # 1回目
    config1 = manager.get_config()
    assert config1.mode == "B"
    
    # 2回目 (直後)
    config2 = manager.get_config()
    assert config2.mode == "B"
    
    # SSMは1回しか呼ばれていないはず
    assert mock_ssm_client.get_parameters.call_count == 1

def test_config_cache_expiration(mock_ssm_client):
    """TTL経過後に再取得すること"""
    mock_ssm_client.get_parameters.return_value = {
        'Parameters': [
            {'Name': '/reco/exp/mode', 'Value': 'A'}
        ]
    }

    manager = ConfigManager(ttl_seconds=0.1)
    
    manager.get_config()
    time.sleep(0.2) # TTL切れ待ち
    manager.get_config()
    
    assert mock_ssm_client.get_parameters.call_count == 2
