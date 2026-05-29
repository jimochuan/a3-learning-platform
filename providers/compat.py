"""
=============================================================================
向后兼容层 —— 把 PROVIDERS 注册表映射为旧的 SPARK_CONFIG / DEEPSEEK_CONFIG 等
原有代码通过 from config import SPARK_CONFIG 仍然能正常工作
=============================================================================
"""
from .registry import PROVIDERS


def _pick(key, field, default=None):
    return PROVIDERS[key].get(field, default) if key in PROVIDERS else default


SPARK_CONFIG = {
    "APPID": _pick("spark", "appid"),
    "API_KEY": _pick("spark", "api_key"),
    "API_SECRET": _pick("spark", "api_secret"),
    "MODEL": _pick("spark", "model"),
    "BASE_URL": _pick("spark", "base_url"),
    "TEMPERATURE": _pick("spark", "temperature"),
    "MAX_TOKENS": _pick("spark", "max_tokens"),
}

DEEPSEEK_CONFIG = {
    "API_KEY": _pick("deepseek", "api_key"),
    "MODEL": _pick("deepseek", "model"),
    "BASE_URL": _pick("deepseek", "base_url"),
    "TEMPERATURE": _pick("deepseek", "temperature"),
    "MAX_TOKENS": _pick("deepseek", "max_tokens"),
}

GLM_CONFIG = {
    "API_KEY": _pick("glm", "api_key"),
    "MODEL": _pick("glm", "model"),
    "BASE_URL": _pick("glm", "base_url"),
    "TEMPERATURE": _pick("glm", "temperature"),
    "MAX_TOKENS": _pick("glm", "max_tokens"),
}
