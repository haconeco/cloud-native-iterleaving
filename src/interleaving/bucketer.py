
from src.config import ExperimentConfig

class Bucketer:
    def determine_mode(self, user_hash: int, config: ExperimentConfig) -> str:
        """
        user_hash (int) をもとにサンプリング判定を行い、
        Interleaving対象であれば config.mode ("INTERLEAVE") を返す。
        そうでなければデフォルトの "A" を返す（現在はA固定）。
        
        ハッシュ値の正規化には 10000 の剰余を利用する (0.01%単位)。
        """
        normalized_hash = (user_hash % 10000) / 10000.0
        
        if normalized_hash < config.sampling_rate:
            return config.mode
            
        # Target out, fallback to A (Baseline)
        return "A"
