"""
=============================================================================
模型供应商注册中心 —— 添加新供应商只需在这里加一行配置
所有供应商均提供 OpenAI 兼容接口: /v1/chat/completions
=============================================================================
"""
from dotenv import load_dotenv
load_dotenv()
import os


PROVIDERS = {
    "deepseek": {
        "key": "deepseek",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": "https://api.deepseek.com/v1",
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "label": "DeepSeek",
        "desc":  "主力推荐 · 性价比最高 · 充值 10 元用很久",
        "register_url": "https://platform.deepseek.com",
        "howto": "注册 -> API Keys -> 创建 Key -> 填入 .env 的 DEEPSEEK_API_KEY",
        "temperature": 0.5,
        "max_tokens": 4096,
        "builtin": False,
    },
    "qwen": {
        "key": "qwen",
        "api_key": os.getenv("QWEN_API_KEY", ""),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": os.getenv("QWEN_MODEL", "qwen-plus"),
        "label": "通义千问",
        "desc":  "阿里云 · 有免费额度 · qwen-plus 性价比高",
        "register_url": "https://dashscope.console.aliyun.com",
        "howto": "阿里云 DashScope 控制台 -> API-Key 管理 -> 创建 Key -> 填入 .env 的 QWEN_API_KEY",
        "temperature": 0.5,
        "max_tokens": 4096,
        "builtin": False,
    },
    "moonshot": {
        "key": "moonshot",
        "api_key": os.getenv("MOONSHOT_API_KEY", ""),
        "base_url": "https://api.moonshot.cn/v1",
        "model": os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k"),
        "label": "月之暗面 Kimi",
        "desc":  "长文本专家 · 128k 上下文 · 注册即送额度",
        "register_url": "https://platform.moonshot.cn",
        "howto": "Moonshot 开放平台 -> API Keys -> 创建 -> 填入 .env 的 MOONSHOT_API_KEY",
        "temperature": 0.5,
        "max_tokens": 4096,
        "builtin": False,
    },
    "glm": {
        "key": "glm",
        "api_key": os.getenv("GLM_API_KEY", ""),
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": os.getenv("GLM_MODEL", "glm-4-flash"),
        "label": "智谱 GLM",
        "desc":  "清华系 · glm-4-flash 免费 · 模型线齐全",
        "register_url": "https://open.bigmodel.cn",
        "howto": "智谱开放平台 -> API Keys -> 复制 Key -> 填入 .env 的 GLM_API_KEY",
        "temperature": 0.5,
        "max_tokens": 2048,
        "builtin": False,
    },
    "baichuan": {
        "key": "baichuan",
        "api_key": os.getenv("BAICHUAN_API_KEY", ""),
        "base_url": "https://api.baichuan-ai.com/v1",
        "model": os.getenv("BAICHUAN_MODEL", "Baichuan4-Turbo"),
        "label": "百川智能",
        "desc":  "百川大模型 · Turbo 性价比之选",
        "register_url": "https://platform.baichuan-ai.com",
        "howto": "百川开放平台 -> API Keys -> 创建 -> 填入 .env 的 BAICHUAN_API_KEY",
        "temperature": 0.5,
        "max_tokens": 4096,
        "builtin": False,
    },
    "spark": {
        "key": "spark",
        "api_key": os.getenv("SPARK_API_KEY", "aa9213dc2668ecf35ffd50776e6130bb"),
        "api_secret": os.getenv("SPARK_API_SECRET", "NGU2OWEyNGIyZWE5NmNhMTI1Mzg2YzU0"),
        "appid": os.getenv("SPARK_APPID", "fb979993"),
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "model": os.getenv("SPARK_MODEL", "lite"),
        "label": "讯飞星火",
        "desc":  "系统预置 · 无限额度 · 无需配置即可使用",
        "register_url": "https://console.xfyun.cn",
        "howto": "控制台 -> 星火大模型 -> 免费领取 Lite 额度 -> 填入 .env",
        "temperature": 0.7,
        "max_tokens": 2048,
        "builtin": True,   # 系统预置，不需要用户配置
    },
}

# 用户选择的主力模型，默认 DeepSeek
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "deepseek")


def get_provider(key: str = None) -> dict:
    """获取指定供应商的完整配置，不存在则回退到 DeepSeek"""
    if key is None:
        key = PRIMARY_MODEL
    return PROVIDERS.get(key, PROVIDERS["deepseek"])
