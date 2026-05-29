"""
=============================================================================
A3 v3 安全与防幻觉机制
=============================================================================
三层防护:
  1. Prompt 层 —— 所有 Agent 系统提示词注入防幻觉规则
  2. 后处理层 —— 对生成内容进行关键词/模式检测
  3. 溯源层 —— RAG 和资源的来源标注与可信度评估
=============================================================================
"""
import re
from typing import List, Tuple, Optional


# ============================================================================
# Layer 1: Prompt 层 —— 防幻觉系统提示词
# ============================================================================

ANTI_HALLUCINATION_CLAUSE = """
【防幻觉与内容安全规则 —— 必须严格遵守】
1. 只陈述你确知的内容，不确定的信息必须明确标注"不确定"或"据推测"
2. 不得编造论文标题、书籍名称、URL、统计数据或任何人名
3. 推荐资源时，如果是真实存在的资源请标注来源，否则标注"示例"或"参考方向"
4. 涉及学术概念时必须严谨，混淆不清的概念要主动说明区别
5. 不得生成任何违反中国法律法规的内容
6. 不得对敏感政治话题发表观点
7. 如果学生提问超出课程范围且你无法确认，直接说"这个问题超出了我的知识范围"
8. 代码示例必须可运行（或标注"伪代码"），不得包含安全漏洞"""

# 简版（用于资源生成等非对话场景）
ANTI_HALLUCINATION_SHORT = """
【防幻觉规则】
- 不确定的信息标注"供参考"
- 不编造人名、书名、URL、数据
- 代码示例确保可运行"""


def inject_safety_prompt(system_prompt: str, short: bool = False) -> str:
    """向 Agent 系统提示词注入防幻觉规则

    Args:
        system_prompt: 原始系统提示词
        short: True 使用简版规则

    Returns:
        注入防幻觉规则后的提示词
    """
    clause = ANTI_HALLUCINATION_SHORT if short else ANTI_HALLUCINATION_CLAUSE
    return system_prompt + "\n" + clause


# ============================================================================
# Layer 2: 后处理层 —— 内容安全过滤器
# ============================================================================

# 虚假引用模式：看起来像真实引用但可能是编造的
FAKE_REFERENCE_PATTERNS = [
    (r'\[\d+\]', '方括号引用标记（应替换为明确的来源说明）'),
    (r'\([A-Z][a-z]+,\s*\d{4}\)', '疑似编造的学术引用格式 (Author, Year)'),
    (r'DOI:\s*10\.\d+/', 'DOI 引用（仅当确认真实存在时使用）'),
]

# 需标记的敏感内容关键词（仅检测，不自动拦截）
SENSITIVE_KEYWORDS = [
    '色情', '暴力', '赌博', '毒品', '诈骗',
    '翻墙', 'VPN翻墙', '反动',
]


def content_audit(text: str) -> dict:
    """审核生成内容的可信度和安全性

    Args:
        text: 生成的文本内容

    Returns:
        {
            "safe": True/False,
            "warnings": [警告列表],
            "score": 0-100 (可信度评分)
        }
    """
    warnings = []
    score = 100

    # 1. 检查疑似编造的引用
    for pattern, desc in FAKE_REFERENCE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            warnings.append(f"检测到{desc}: {len(matches)}处")
            score -= min(len(matches) * 5, 20)

    # 2. 检查敏感关键词
    for kw in SENSITIVE_KEYWORDS:
        if kw in text:
            warnings.append(f"包含敏感关键词: '{kw}'")
            score -= 30

    # 3. 检查是否缺少来源标注
    has_source = bool(re.search(r'(来源|参考|引自|出处|根据|Source|Reference)', text))
    if len(text) > 500 and not has_source and any(kw in text for kw in ['研究', '据', '论文', '实验', '数据']):
        warnings.append("内容涉及研究/数据但未标注来源")
        score -= 10

    # 4. 检查自相矛盾的陈述
    # （简化版：检测常见的矛盾短语）
    contradictions = [
        (r'一定.*不一定', '自相矛盾: 确定性与不确定性并存'),
        (r'必须.*可选', '自相矛盾: 强制与可选并存'),
    ]
    for pattern, desc in contradictions:
        if re.search(pattern, text):
            warnings.append(desc)
            score -= 15

    safe = score >= 60 and not any(kw in text for kw in SENSITIVE_KEYWORDS)

    return {
        "safe": safe,
        "warnings": warnings,
        "score": max(score, 0),
    }


# ============================================================================
# Layer 3: 溯源层 —— 来源标注
# ============================================================================

def generate_source_notice(sources: List[dict]) -> str:
    """为生成内容生成来源标注

    Args:
        sources: [{"title": "...", "type": "教材/论文/网站", "url": "..."}]

    Returns:
        来源标注文本
    """
    if not sources:
        return "\n\n---\n*⚠️ 以上内容由AI生成，未找到明确的参考来源。建议通过教材或其他权威渠道核实。*"

    lines = ["\n\n---\n### 📖 内容来源"]
    for i, s in enumerate(sources, 1):
        title = s.get("title", "未知来源")
        stype = s.get("type", "")
        url = s.get("url", "")
        type_str = f" ({stype})" if stype else ""
        url_str = f" - {url}" if url else ""
        lines.append(f"{i}. {title}{type_str}{url_str}")
    return "\n".join(lines)


def uncertainty_marker(content: str, confidence: str = "high") -> str:
    """为不确定内容添加标记

    Args:
        content: 原始内容
        confidence: high / medium / low

    Returns:
        处理后的内容
    """
    markers = {
        "high": "",
        "medium": "\n\n> 💡 *以上部分内容为AI推断，建议验证。*",
        "low": "\n\n> ⚠️ *以上内容AI置信度较低，仅供参考，请以教材为准。*",
    }
    return content + markers.get(confidence, markers["medium"])


# ============================================================================
# 综合防护函数
# ============================================================================

def safe_generate(raw_output: str, sources: List[dict] = None,
                  confidence: str = "high") -> Tuple[str, dict]:
    """对 Agent 输出进行综合安全处理

    Args:
        raw_output: Agent 原始输出
        sources: 来源列表（可选）
        confidence: 置信度 high/medium/low

    Returns:
        (safe_output, audit_result)
    """
    # Step 1: 内容审核
    audit = content_audit(raw_output)

    # Step 2: 置信度标记
    output = uncertainty_marker(raw_output, confidence)

    # Step 3: 来源标注
    output += generate_source_notice(sources or [])

    # Step 4: 如果不安全，追加警告
    if not audit["safe"]:
        output = "> ⚠️ **内容安全提示**: 以下内容可能包含不准确的信息，请谨慎参考。\n\n" + output

    return output, audit
