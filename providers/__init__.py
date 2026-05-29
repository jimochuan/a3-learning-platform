"""
=============================================================================
providers —— 多模型供应商模块
新增供应商只需在 registry.py 加一行，无需改其他文件
=============================================================================

用法:
    from providers import make_model, primary_model, spark_model, SafeOpenAIChat
    from providers import test_api_connectivity, PROVIDERS, PRIMARY_MODEL
    from providers.compat import SPARK_CONFIG, DEEPSEEK_CONFIG, GLM_CONFIG
"""
from .factory import SafeOpenAIChat, make_model, primary_model, spark_model
from .registry import PROVIDERS, PRIMARY_MODEL, get_provider
from .diagnostics import test_api_connectivity
