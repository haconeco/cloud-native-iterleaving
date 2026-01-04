
import time
import boto3
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ExperimentConfig:
    mode: str
    sampling_rate: float
    parallel_enabled: bool
    interleave_method: str = "team_draft"

class ConfigManager:
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._cached_config: Optional[ExperimentConfig] = None
        self._last_fetched_at: float = 0.0
        self._ssm_client = boto3.client('ssm')

    def get_config(self) -> ExperimentConfig:
        current_time = time.time()
        
        if self._cached_config and (current_time - self._last_fetched_at < self.ttl_seconds):
            return self._cached_config
            
        try:
            config = self._fetch_from_ssm()
            self._cached_config = config
            self._last_fetched_at = current_time
            return config
        except Exception as e:
            # エラーログを出力すべきだが、ここでは最小実装としてデフォルトを返す
            # print(f"Error fetching config: {e}") 
            return self._get_default_config()

    def _fetch_from_ssm(self) -> ExperimentConfig:
        names = [
            '/reco/exp/mode',
            '/reco/exp/sampling_rate',
            '/reco/exp/parallel_enabled',
            '/reco/exp/interleave_method'
        ]
        
        response = self._ssm_client.get_parameters(Names=names)
        params = {p['Name']: p['Value'] for p in response.get('Parameters', [])}
        
        mode = params.get('/reco/exp/mode', 'A')
        sampling_rate = float(params.get('/reco/exp/sampling_rate', '0.0'))
        
        # parallel_enabled assumes "true" (case-insensitive) is True
        parallel_str = params.get('/reco/exp/parallel_enabled', 'false').lower()
        parallel_enabled = parallel_str == 'true'

        interleave_method = params.get('/reco/exp/interleave_method', 'team_draft')
        
        return ExperimentConfig(
            mode=mode,
            sampling_rate=sampling_rate,
            parallel_enabled=parallel_enabled,
            interleave_method=interleave_method
        )

    def _get_default_config(self) -> ExperimentConfig:
        # 安全側に倒す(Mode A, no sampling)
        return ExperimentConfig(
            mode="A",
            sampling_rate=0.0,
            parallel_enabled=False,
            interleave_method="team_draft"
        )
