"""
=============================================================================
API 连通性诊断 —— 启动时对每家供应商发一条最短请求，验证能否正常调用
=============================================================================
"""
import os
import time as _time

from .registry import PROVIDERS, PRIMARY_MODEL


def test_api_connectivity() -> dict:
    """启动时实际调用各家 API，验证连通性。

    Returns:
        { "<provider_key>": { ready, connected, latency_ms, error, label, ... },
          "any_connected": bool,
          "primary_connected": bool,
          "primary_key": str,
          "_primary": dict }
    """
    results = {}
    test_msg = [{"role": "user", "content": "回 OK"}]
    primary_connected = False
    any_connected = False

    for pkey, cfg in PROVIDERS.items():
        ready = cfg.get("builtin", False) or bool(cfg["api_key"])
        connected = False
        latency = 0
        error = None

        if ready:
            try:
                from openai import OpenAI
                api_key = cfg["api_key"]
                if cfg.get("api_secret"):
                    api_key = f"{cfg['api_key']}:{cfg['api_secret']}"

                client = OpenAI(
                    api_key=api_key,
                    base_url=cfg["base_url"],
                    timeout=15,
                )
                t0 = _time.time()
                resp = client.chat.completions.create(
                    model=cfg["model"],
                    messages=test_msg,
                    max_tokens=5,
                    temperature=0,
                )
                resp.choices[0].message.content
                latency = int((_time.time() - t0) * 1000)
                connected = True
            except Exception as e:
                error = _classify_error(e)

        results[pkey] = {
            "ready": ready,
            "connected": connected,
            "latency_ms": latency,
            "error": error,
            "label": cfg["label"],
            "desc": cfg["desc"],
            "register_url": cfg["register_url"],
            "howto": cfg["howto"],
            "builtin": cfg.get("builtin", False),
        }

        if connected:
            any_connected = True
            if pkey == PRIMARY_MODEL:
                primary_connected = True

    results["any_connected"] = any_connected
    results["primary_connected"] = primary_connected
    results["primary_key"] = PRIMARY_MODEL
    results["_primary"] = PROVIDERS.get(PRIMARY_MODEL, PROVIDERS["deepseek"])

    return results


def _classify_error(exc: Exception) -> str:
    """把 API 异常归类成用户能看懂的中文提示"""
    msg = str(exc)
    if "401" in msg or "403" in msg or "unauthorized" in msg.lower() or "invalid" in msg.lower():
        return "Key 无效或已过期，请检查是否复制正确"
    if "429" in msg or "rate" in msg.lower() or "quota" in msg.lower():
        return "API 额度用完或请求太频繁，稍后再试"
    if "timeout" in msg.lower() or "timed out" in msg:
        return "连接超时，请检查网络或防火墙"
    if "refused" in msg.lower() or "resolve" in msg.lower() or "connect" in msg.lower():
        return "无法连接到 API 服务器，请检查网络"
    return f"未知错误: {msg[:150]}"
