"""
=============================================================================
模型工厂 —— 统一创建任意供应商的 SafeOpenAIChat 实例
=============================================================================
"""
from phi.model.openai import OpenAIChat

from .registry import PROVIDERS, PRIMARY_MODEL


# ============================================================================
# SafeOpenAIChat —— 兼容所有不支持 developer role 的 OpenAI 兼容 API
# ============================================================================
class SafeOpenAIChat(OpenAIChat):
    """强制保留 system role（不转 developer）。

    兼容: DeepSeek / 讯飞星火 / 通义千问 / GLM / Moonshot / 百川 等"""

    _role_patched = True

    def format_message(self, message, map_system_to_developer=False):
        return super().format_message(message, map_system_to_developer=False)

    def invoke(self, messages, *args, **kwargs):
        return super().invoke(messages, *args, **kwargs)

    def invoke_stream(self, messages, *args, **kwargs):
        return super().invoke_stream(messages, *args, **kwargs)

    def response(self, messages, *args, **kwargs):
        return super().response(messages, *args, **kwargs)

    def response_stream(self, messages, *args, **kwargs):
        return super().response_stream(messages, *args, **kwargs)


# ============================================================================
# 模型创建
# ============================================================================
def make_model(provider_key: str = None, temperature: float = 0.7) -> SafeOpenAIChat:
    """根据供应商 key 创建 SafeOpenAIChat 实例"""
    if provider_key is None:
        provider_key = PRIMARY_MODEL

    cfg = PROVIDERS.get(provider_key)
    if cfg is None:
        raise ValueError(f"未知的模型供应商: {provider_key}。可选: {list(PROVIDERS.keys())}")

    api_key = cfg["api_key"]
    if cfg.get("api_secret"):
        api_key = f"{cfg['api_key']}:{cfg['api_secret']}"

    return SafeOpenAIChat(
        id=cfg["model"],
        base_url=cfg["base_url"],
        api_key=api_key,
        temperature=temperature,
        max_tokens=cfg.get("max_tokens", 4096),
    )


def primary_model(temperature: float = 0.7) -> SafeOpenAIChat:
    """主力模型：由 PRIMARY_MODEL 环境变量决定，默认 DeepSeek"""
    return make_model(PRIMARY_MODEL, temperature)


def spark_model(temperature: float = 0.7) -> SafeOpenAIChat:
    """备用模型：讯飞星火"""
    return make_model("spark", temperature)
