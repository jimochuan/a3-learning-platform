"""
=============================================================================
A3 v3 Agent Graph —— LangGraph 协作图
六智能体协作编排：Profile → Resource → Roadmap → Tutor ⇄ Weakness → Eval

Phase 2: 基础设施 — 定义 StateGraph、6 个节点、路由规则
Phase 3: 逐个迁移 Agent
Phase 4: 协作链 Tutor→Weakness→Eval→Roadmap 自动触发

依赖: langgraph>=1.0, agents.py, shared_context.py, dialogue_resource_agent.py
=============================================================================
"""
import json
import logging
from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from config import DEEPSEEK_CONFIG
from agents import StudyAgents, run_with_fallback
from shared_context import AgentContext, StudentProfile, TutorSession

logger = logging.getLogger(__name__)


# ============================================================================
# AgentState —— LangGraph 状态定义
# ============================================================================
class AgentState(TypedDict, total=False):
    """LangGraph 全局状态，在各 Agent 节点间流转

    使用 TypedDict 而非 Pydantic（LangGraph 原生支持更好）。
    字段与 AgentContext 保持对应，方便互转。
    """

    # ---- 用户标识 ----
    uid: str
    course_name: str

    # ---- Agent 输出（序列化为 JSON/str 以保持兼容性）----
    profile_raw: str           # StudentProfile JSON
    resources_raw: str         # LearningResources JSON (包含 report_markdown)
    roadmap_raw: str           # LearningRoadmap JSON (包含 report_markdown)
    tutor_history: str         # TutorSession JSON (含 chat_history + weakness_records)
    weakness_raw: str          # Weakness 诊断报告 Markdown
    eval_raw: str              # EvaluationReport JSON (含 report_markdown)

    # ---- 控制流 ----
    target_node: str           # 路由目标: profile|resource|roadmap|tutor|weakness|eval
    current_phase: str         # 当前阶段（与 target_node 保持一致）
    next_phase: str            # 完成后跳转到哪个阶段（''表示不跳转）

    # ---- 协作触发器 ----
    pending_weakness: bool     # Tutor 检测到薄弱点 → 触发 Weakness Agent
    pending_eval_update: bool  # Weakness 完成 → 触发 Eval
    pending_roadmap_adjust: bool  # Eval 完成 → 触发 Roadmap 调整

    # ---- 节点输入（供各节点读取）----
    user_message: str          # 用户最新消息（Profile/Tutor 交互用）
    system_instruction: str    # 额外系统指令（跨节点传递）
    weakness_detail: str       # 薄弱点详情（topic|||student_ans|||correct_ans 格式）

    # ---- 错误 ----
    error: str                 # 最近一次错误信息


# ============================================================================
# 状态转换辅助函数
# ============================================================================
def ctx_to_state(ctx: AgentContext) -> AgentState:
    """AgentContext → AgentState"""
    state: AgentState = {
        "uid": ctx.uid,
        "course_name": ctx.course_name,
        "current_phase": ctx.current_phase,
        "next_phase": "",
        "pending_weakness": ctx.pending_weakness,
        "pending_eval_update": ctx.pending_eval_update,
        "pending_roadmap_adjust": ctx.pending_roadmap_adjust,
        "user_message": "",
        "system_instruction": "",
        "error": "",
    }
    # 序列化各 Agent 输出
    if ctx.profile:
        state["profile_raw"] = json.dumps(ctx.profile.to_dict(), ensure_ascii=False)
    if ctx.resources:
        state["resources_raw"] = json.dumps(ctx.resources.to_dict(), ensure_ascii=False)
    if ctx.roadmap:
        state["roadmap_raw"] = json.dumps(ctx.roadmap.to_dict(), ensure_ascii=False)
    if ctx.tutor_session:
        state["tutor_history"] = json.dumps(ctx.tutor_session.to_dict(), ensure_ascii=False)
    if ctx.evaluation:
        state["eval_raw"] = json.dumps(ctx.evaluation.to_dict(), ensure_ascii=False)
    return state


def state_to_ctx(state: AgentState) -> AgentContext:
    """AgentState → AgentContext"""
    ctx = AgentContext(
        uid=state.get("uid", ""),
        course_name=state.get("course_name", ""),
        current_phase=state.get("current_phase", "profile"),
        pending_weakness=state.get("pending_weakness", False),
        pending_eval_update=state.get("pending_eval_update", False),
        pending_roadmap_adjust=state.get("pending_roadmap_adjust", False),
    )
    ctx.stamp()

    # 反序列化
    if state.get("profile_raw"):
        try:
            d = json.loads(state["profile_raw"])
            ctx.profile = StudentProfile.from_dict(d)
        except json.JSONDecodeError:
            pass

    if state.get("resources_raw"):
        try:
            from shared_context import LearningResources
            d = json.loads(state["resources_raw"])
            ctx.resources = LearningResources.from_dict(d)
        except json.JSONDecodeError:
            pass

    if state.get("roadmap_raw"):
        try:
            from shared_context import LearningRoadmap
            d = json.loads(state["roadmap_raw"])
            ctx.roadmap = LearningRoadmap.from_dict(d)
        except json.JSONDecodeError:
            pass

    if state.get("tutor_history"):
        try:
            d = json.loads(state["tutor_history"])
            ctx.tutor_session = TutorSession.from_dict(d)
        except json.JSONDecodeError:
            pass

    if state.get("eval_raw"):
        try:
            from shared_context import EvaluationReport
            d = json.loads(state["eval_raw"])
            ctx.evaluation = EvaluationReport.from_dict(d)
        except json.JSONDecodeError:
            pass

    return ctx


# ============================================================================
# 节点函数
# ============================================================================

# 全局 Agent 工厂实例（延迟初始化，避免启动时连接模型）
_agents_factory: Optional[StudyAgents] = None


def _get_agents(course_name: str = "") -> StudyAgents:
    """获取或创建 StudyAgents 实例"""
    global _agents_factory
    if _agents_factory is None or (course_name and _agents_factory.course_name != course_name):
        _agents_factory = StudyAgents(course_name=course_name)
    return _agents_factory


# ---- Node 1: Profile Agent ----
def profile_node(state: AgentState) -> AgentState:
    """画像节点：分析学生特征，生成 StudentProfile

    输入: state["user_message"] (最新用户消息) + state["profile_raw"] (已有画像，如有)
    输出: state["profile_raw"] (更新后的画像 JSON)
    """
    update: AgentState = {"error": ""}

    try:
        course = state.get("course_name", "")
        agents = _get_agents(course)
        agent = agents.profile_agent()

        # 构建 prompt：如果已有部分画像，追加已有信息
        existing_raw = state.get("profile_raw", "")
        user_msg = state.get("user_message", "")

        # 将中文画像转回中文格式供 Agent 理解
        existing_cn = ""
        if existing_raw:
            try:
                from shared_context import StudentProfile
                sp = StudentProfile.from_dict(json.loads(existing_raw))
                existing_cn = json.dumps(sp.to_chinese_dict(), ensure_ascii=False)
            except (json.JSONDecodeError, Exception):
                existing_cn = existing_raw

        if existing_cn:
            prompt = f"""以下是已提取的学生画像:
{existing_cn}

学生最新的回答:
{user_msg}

请根据学生的最新回答更新画像。如果学生提供了新的信息，更新对应维度。
输出格式: 仅输出更新后的完整 JSON，每个维度一句话总结。
{{
    "知识基础": "...",
    "认知风格": "...",
    "学习目标": "...",
    "薄弱环节": "...",
    "学习节奏": "...",
    "兴趣领域": "..."
}}"""
        else:
            prompt = f"""当前课程: {course}

学生的回答: "{user_msg}"

请从学生发言中提取以下6个维度的信息。未提到的标注"待了解"。
输出格式: 仅输出 JSON:
{{
    "知识基础": "...",
    "认知风格": "...",
    "学习目标": "...",
    "薄弱环节": "...",
    "学习节奏": "...",
    "兴趣领域": "..."
}}"""

        resp, model_name = run_with_fallback(agent, prompt)

        # 将中文 key 映射为英文字段名后再存储
        try:
            raw_data = json.loads(resp)
            from shared_context import StudentProfile
            sp = StudentProfile.from_dict(raw_data)
            update["profile_raw"] = json.dumps(sp.to_dict(), ensure_ascii=False)
        except json.JSONDecodeError:
            # LLM 可能返回非纯 JSON，尝试提取 JSON 块
            import re
            match = re.search(r'\{[^}]+\}', resp, re.DOTALL)
            if match:
                try:
                    raw_data = json.loads(match.group())
                    from shared_context import StudentProfile
                    sp = StudentProfile.from_dict(raw_data)
                    update["profile_raw"] = json.dumps(sp.to_dict(), ensure_ascii=False)
                except (json.JSONDecodeError, Exception):
                    update["profile_raw"] = resp  # 原样存储
            else:
                update["profile_raw"] = resp  # 原样存储

        update["current_phase"] = "profile"
        logger.info(f"Profile Agent 完成 (模型: {model_name})")

    except Exception as e:
        update["error"] = f"Profile Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ---- Node 2: Resource Agent ----
def resource_node(state: AgentState) -> AgentState:
    """资源节点：根据画像生成个性化学习资源

    输入: state["profile_raw"] + state["course_name"]
    输出: state["resources_raw"]
    """
    update: AgentState = {"error": ""}

    try:
        course = state.get("course_name", "")
        profile_raw = state.get("profile_raw", "{}")

        try:
            profile_dict = json.loads(profile_raw)
        except json.JSONDecodeError:
            profile_dict = {}

        # 将英文字段名转回中文 key（DialogueResourceAgent 需要中文 key）
        cn_profile = {}
        KEY_MAP_REV = {
            "knowledge_base": "知识基础", "cognitive_style": "认知风格",
            "learning_goals": "学习目标", "weak_areas": "薄弱环节",
            "learning_pace": "学习节奏", "interests": "兴趣领域",
        }
        for eng_key, cn_key in KEY_MAP_REV.items():
            if profile_dict.get(eng_key) and profile_dict[eng_key] != "待了解":
                cn_profile[cn_key] = profile_dict[eng_key]

        # 使用对话资源智能体 (dialogue_resource_agent.py)
        from dialogue_resource_agent import DialogueResourceAgent

        dra = DialogueResourceAgent(course_name=course, profile=cn_profile)
        report = dra.generate_report()

        # 第5种资源: 知识结构图 (LLM 生成)
        try:
            agents = _get_agents(course)
            km_agent = agents.resource_agent()
            km_prompt = f"""请为课程"{course}"生成一份知识结构图（知识体系树状图）。

要求:
- 用 ASCII 树状图/大纲展示课程的核心知识体系
- 标注各模块的层级关系（基础→进阶→高级）
- 标注重点(★)和难点(▲)
- 根据学生薄弱环节，在对应节点标注"需加强"

学生画像: {json.dumps(cn_profile, ensure_ascii=False) if cn_profile else '无'}

只输出知识结构图，不要其他内容。"""
            km_resp, _ = run_with_fallback(km_agent, km_prompt)
            if km_resp and len(km_resp) > 20:
                report += "\n\n---\n\n## \U0001F7E0 知识结构图（第5类资源）\n\n"
                report += km_resp
        except Exception:
            pass  # 知识结构图生成失败不影响主流程

        from shared_context import LearningResources
        resources = LearningResources(
            course_name=course,
            preferences=dra.extracted.get("preferences", []),
            local_resources=[],    # generate_report 已包含资源列表在 markdown 中
            network_resources=[],
            report_markdown=report,
            updated_at=datetime.now().isoformat(),
        )
        update["resources_raw"] = json.dumps(resources.to_dict(), ensure_ascii=False)
        update["current_phase"] = "resource"
        logger.info("Resource Agent 完成")

    except Exception as e:
        update["error"] = f"Resource Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ---- Node 3: Roadmap Agent ----
def roadmap_node(state: AgentState) -> AgentState:
    """路径节点：根据画像 + 薄弱点 生成个性化学习路径

    输入: state["profile_raw"] + state["weakness_raw"]
    输出: state["roadmap_raw"]
    """
    update: AgentState = {"error": ""}

    try:
        course = state.get("course_name", "")
        agents = _get_agents(course)
        agent = agents.roadmap_agent()

        # 构建 prompt：包含画像和薄弱点信息（转中文 key）
        profile_raw = state.get("profile_raw", "")
        weakness_raw = state.get("weakness_raw", "")

        prompt_parts = [f"请为以下学生规划{course}的个性化学习路径。"]
        if profile_raw:
            try:
                from shared_context import StudentProfile
                sp = StudentProfile.from_dict(json.loads(profile_raw))
                cn_profile = json.dumps(sp.to_chinese_dict(), ensure_ascii=False)
                prompt_parts.append(f"\n学生画像:\n{cn_profile}")
            except (json.JSONDecodeError, Exception):
                prompt_parts.append(f"\n学生画像:\n{profile_raw}")

        # 加入资源信息，帮助路径和资源对应
        resources_raw = state.get("resources_raw", "")
        if resources_raw:
            try:
                res_data = json.loads(resources_raw)
                res_md = res_data.get("report_markdown", "")
                if res_md:
                    prompt_parts.append(f"\n已推荐资源摘要:\n{res_md[:800]}")
            except (json.JSONDecodeError, Exception):
                pass

        if weakness_raw:
            prompt_parts.append(f"\n已知薄弱点:\n{weakness_raw}")
        prompt_parts.append("\n请生成5-8步学习路径，Markdown表格格式。")

        resp, model_name = run_with_fallback(agent, "\n".join(prompt_parts))

        from shared_context import LearningRoadmap
        roadmap = LearningRoadmap(
            course_name=course,
            report_markdown=resp,
            updated_at=datetime.now().isoformat(),
        )
        update["roadmap_raw"] = json.dumps(roadmap.to_dict(), ensure_ascii=False)
        update["current_phase"] = "roadmap"
        logger.info(f"Roadmap Agent 完成 (模型: {model_name})")

    except Exception as e:
        update["error"] = f"Roadmap Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ---- Node 4: Tutor Agent ----
def tutor_node(state: AgentState) -> AgentState:
    """辅导节点：处理一轮辅导对话

    输入: state["user_message"] + state["tutor_history"]
    输出: state["tutor_history"] (追加最新一轮对话)
          如果检测到 [WEAKNESS:...] → state["pending_weakness"] = True
    """
    update: AgentState = {"error": ""}

    try:
        course = state.get("course_name", "")
        agents = _get_agents(course)
        agent = agents.tutor_agent()

        user_msg = state.get("user_message", "")
        history_raw = state.get("tutor_history", "")

        # 构建对话上下文
        chat_history = []
        if history_raw:
            try:
                session = json.loads(history_raw)
                chat_history = session.get("chat_history", [])
            except json.JSONDecodeError:
                pass

        # 构建 prompt（包含历史对话）
        context = ""
        for msg in chat_history[-6:]:  # 最近3轮
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context += f"{'学生' if role == 'user' else '老师'}: {content}\n"

        prompt = f"""当前课程: {course}

对话历史:
{context}

学生最新消息: {user_msg}

请作为辅导老师回复学生。你可以:
1. 讲解概念（如果学生在提问）
2. 出测验题（如果学生要求或你刚讲完一个知识点）
3. 如果学生答错了，在你的回复末尾标注: [WEAKNESS:主题|学生答案|正确答案]

请用友好鼓励的语气回复。"""

        resp, model_name = run_with_fallback(agent, prompt)

        # 检测薄弱点标记
        has_weakness = "[WEAKNESS:" in resp
        if has_weakness:
            update["pending_weakness"] = True
            logger.info("检测到薄弱点标记，将触发 Weakness Agent")

        # 更新对话历史
        chat_history.append({"role": "user", "content": user_msg})
        chat_history.append({"role": "assistant", "content": resp})

        from shared_context import TutorSession
        session = TutorSession(
            chat_history=chat_history,
            total_questions_asked=sum(1 for m in chat_history if m["role"] == "assistant" and "?" in m.get("content", "")),
            updated_at=datetime.now().isoformat(),
        )

        # 保留已有的 weakness_records
        if history_raw:
            try:
                old = json.loads(history_raw)
                session.weakness_records = old.get("weakness_records", [])
            except json.JSONDecodeError:
                pass

        update["tutor_history"] = json.dumps(session.to_dict(), ensure_ascii=False)
        update["current_phase"] = "tutor"
        logger.info(f"Tutor Agent 完成 (模型: {model_name})")

    except Exception as e:
        update["error"] = f"Tutor Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ---- Node 5: Weakness Agent ----
def weakness_node(state: AgentState) -> AgentState:
    """薄弱点分析节点：分析学生答错的原因，生成补救方案

    触发条件: state["pending_weakness"] == True
    输入: state["tutor_history"] (获取最新一轮的 [WEAKNESS:...] 标记)
    输出: state["weakness_raw"] + 更新 state["tutor_history"].weakness_records
    """
    update: AgentState = {"error": "", "pending_weakness": False}

    try:
        course = state.get("course_name", "")
        agents = _get_agents(course)
        agent = agents.weakness_agent()

        # 优先使用显式传入的 weakness_detail（Phase 4 协作链）
        explicit_detail = state.get("weakness_detail", "")
        weakness_info = ""
        history_raw = state.get("tutor_history", "")  # Always fetch for record-keeping

        if explicit_detail:
            # 格式: topic|||student_ans|||correct_ans
            parts = explicit_detail.split("|||")
            if len(parts) >= 3:
                weakness_info = (
                    f"[WEAKNESS:{parts[0]}|{parts[1]}|{parts[2]}]\n"
                    f"知识点: {parts[0]}\n"
                    f"学生回答: {parts[1]}\n"
                    f"正确答案: {parts[2]}"
                )
            else:
                weakness_info = explicit_detail
        elif history_raw:
            # Fallback: 从 tutor_history 中提取 WEAKNESS 标记
            try:
                session = json.loads(history_raw)
                chat_history = session.get("chat_history", [])
                for msg in reversed(chat_history):
                    if msg["role"] == "assistant" and "[WEAKNESS:" in msg.get("content", ""):
                        content = msg["content"]
                        start = content.find("[WEAKNESS:")
                        end = content.find("]", start)
                        if end > start:
                            weakness_info = content[start:end+1]
                        break
            except json.JSONDecodeError:
                pass

        prompt = f"""当前课程: {course}

辅导对话中检测到以下薄弱点:
{weakness_info}

请进行薄弱点诊断。输出格式:
## 薄弱点诊断
（1-2句分析为什么会错）

## 补充讲解
（用不同角度重新讲解，更通俗）

## 推荐补救资源
- 资源1: xxx
- 资源2: xxx

## 路径调整建议
（指出学习路径中需要加强的步骤）"""

        resp, model_name = run_with_fallback(agent, prompt)

        update["weakness_raw"] = resp
        update["pending_eval_update"] = True
        update["current_phase"] = "weakness"

        # 将薄弱点诊断追加到 tutor_session（无历史时新建）
        weakness_topic = ""
        if "|||" in state.get("weakness_detail", ""):
            weakness_topic = state["weakness_detail"].split("|||")[0]
        elif "|" in weakness_info:
            weakness_topic = weakness_info.split("|")[0].replace("[WEAKNESS:", "")

        if history_raw:
            try:
                session_data = json.loads(history_raw)
                session_data.setdefault("weakness_records", []).append({
                    "topic": weakness_topic,
                    "diagnosis": resp,
                    "timestamp": datetime.now().isoformat(),
                })
                update["tutor_history"] = json.dumps(session_data, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        else:
            # No existing tutor history — create new session for the weakness record
            from shared_context import TutorSession
            new_session = TutorSession(
                weakness_records=[{
                    "topic": weakness_topic,
                    "diagnosis": resp,
                    "timestamp": datetime.now().isoformat(),
                }],
                updated_at=datetime.now().isoformat(),
            )
            update["tutor_history"] = json.dumps(new_session.to_dict(), ensure_ascii=False)

        logger.info(f"Weakness Agent 完成 (模型: {model_name})")

    except Exception as e:
        update["error"] = f"Weakness Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ---- Node 6: Eval Agent ----
def eval_node(state: AgentState) -> AgentState:
    """评估节点：综合所有数据生成学习评估报告

    触发条件: 手动触发或 state["pending_eval_update"] == True
    输入: state["profile_raw"] + state["tutor_history"] + state["weakness_raw"]
    输出: state["eval_raw"]
    """
    update: AgentState = {"error": "", "pending_eval_update": False}

    try:
        course = state.get("course_name", "")
        agents = _get_agents(course)

        # 收集评估所需数据
        profile_raw = state.get("profile_raw", "")
        history_raw = state.get("tutor_history", "")
        weakness_raw = state.get("weakness_raw", "")

        eval_data_parts = [f"课程: {course}\n"]
        if profile_raw:
            eval_data_parts.append(f"学生画像:\n{profile_raw}")
        if history_raw:
            try:
                session = json.loads(history_raw)
                chat_history = session.get("chat_history", [])
                eval_data_parts.append(f"\n辅导对话记录（共{len(chat_history)}条）:")
                for msg in chat_history[-10:]:
                    eval_data_parts.append(f"  - {'学生' if msg['role']=='user' else '老师'}: {msg['content'][:100]}")
            except json.JSONDecodeError:
                pass
        if weakness_raw:
            eval_data_parts.append(f"\n薄弱点分析:\n{weakness_raw}")

        eval_data = "\n".join(eval_data_parts)

        # 交叉验证评估
        result = agents.cross_validate(eval_data)

        from shared_context import EvaluationReport
        report = EvaluationReport(
            report_markdown=result.get("merged", result.get("glm", "")),
            cross_validation=result.get("spark", ""),
            updated_at=datetime.now().isoformat(),
        )
        update["eval_raw"] = json.dumps(report.to_dict(), ensure_ascii=False)
        update["pending_roadmap_adjust"] = True
        update["current_phase"] = "eval"
        logger.info("Eval Agent 完成（含交叉验证）")

    except Exception as e:
        update["error"] = f"Eval Agent 错误: {e}"
        logger.error(update["error"])

    return update


# ============================================================================
# 路由逻辑
# ============================================================================
def _route_by_target(state: AgentState) -> str:
    """根据 target_node 路由到对应节点"""
    target = state.get("target_node", "profile")
    valid_nodes = {"profile", "resource", "roadmap", "tutor", "weakness", "eval"}
    if target in valid_nodes:
        return target
    return "profile"  # 默认


def _route_after_tutor(state: AgentState) -> str:
    """Tutor 节点完成后的路由决策"""
    if state.get("pending_weakness"):
        return "weakness"
    return "done"


def _route_after_weakness(state: AgentState) -> str:
    """Weakness 节点完成后的路由决策"""
    if state.get("pending_eval_update"):
        return "eval"
    return "done"


def _route_after_eval(state: AgentState) -> str:
    """Eval 节点完成后的路由决策"""
    if state.get("pending_roadmap_adjust"):
        return "roadmap"
    return "done"


# ============================================================================
# 构建 Graph
# ============================================================================
def create_agent_graph():
    """创建并编译 LangGraph 协作图

    Returns:
        编译后的 StateGraph (可调用 .invoke(state) 或 .stream(state))
    """
    builder = StateGraph(AgentState)

    # ---- 注册节点 ----
    builder.add_node("profile", profile_node)
    builder.add_node("resource", resource_node)
    builder.add_node("roadmap", roadmap_node)
    builder.add_node("tutor", tutor_node)
    builder.add_node("weakness", weakness_node)
    builder.add_node("eval", eval_node)

    # ---- 入口路由 ----
    builder.add_edge(START, "router")
    builder.add_node("router", lambda s: {"current_phase": s.get("target_node", "profile")})

    # ---- 从 router 分发到目标节点 ----
    builder.add_conditional_edges(
        "router",
        lambda s: s.get("target_node", "profile"),
        {
            "profile": "profile",
            "resource": "resource",
            "roadmap": "roadmap",
            "tutor": "tutor",
            "weakness": "weakness",
            "eval": "eval",
        }
    )

    # ---- 各节点完成后的路由 ----
    # Profile/Resource/Roadmap → 直接结束（单步调用模式）
    builder.add_edge("profile", END)
    builder.add_edge("resource", END)
    builder.add_edge("roadmap", END)

    # Tutor → 根据是否有薄弱点决定是否触发下游
    builder.add_conditional_edges(
        "tutor",
        _route_after_tutor,
        {"weakness": "weakness", "done": END}
    )

    # Weakness → Eval（自动触发）
    builder.add_conditional_edges(
        "weakness",
        _route_after_weakness,
        {"eval": "eval", "done": END}
    )

    # Eval → Roadmap（自动触发路径调整）
    builder.add_conditional_edges(
        "eval",
        _route_after_eval,
        {"roadmap": "roadmap", "done": END}
    )

    # ---- 编译 ----
    graph = builder.compile()
    logger.info("Agent Graph 编译完成")
    return graph


# ============================================================================
# 便捷调用函数
# ============================================================================
def run_agent_step(
    ctx: AgentContext,
    target: Literal["profile", "resource", "roadmap", "tutor", "weakness", "eval"],
    user_message: str = "",
) -> AgentContext:
    """执行单个 Agent 步骤

    将 AgentContext 转为 AgentState → 执行目标节点 → 转回 AgentContext

    Args:
        ctx: 当前 AgentContext
        target: 要执行的节点名
        user_message: 用户输入（profile/tutor 节点需要）

    Returns:
        更新后的 AgentContext
    """
    state = ctx_to_state(ctx)
    state["target_node"] = target
    state["user_message"] = user_message

    graph = create_agent_graph()

    try:
        result = graph.invoke(state)
        new_ctx = state_to_ctx(result)
        return new_ctx
    except Exception as e:
        ctx.log_error(f"Graph invoke 失败 [{target}]: {e}")
        return ctx


def run_weakness_chain(ctx: AgentContext, weakness_detail: str = "") -> AgentContext:
    """运行完整的薄弱点处理链: Weakness → Eval → Roadmap

    当 Tutor 检测到 [WEAKNESS:...] 后调用此函数，
    自动完成诊断、评估更新、路径调整。

    Args:
        ctx: 当前 AgentContext
        weakness_detail: 薄弱点详情，格式为 "topic|||student_ans|||correct_ans"
    """
    state = ctx_to_state(ctx)
    state["target_node"] = "weakness"
    state["pending_weakness"] = True
    if weakness_detail:
        state["weakness_detail"] = weakness_detail

    graph = create_agent_graph()

    try:
        result = graph.invoke(state)
        new_ctx = state_to_ctx(result)
        return new_ctx
    except Exception as e:
        ctx.log_error(f"Weakness chain 失败: {e}")
        return ctx


# ============================================================================
# 测试入口
# ============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("  Agent Graph 编译测试")
    print("=" * 60)

    graph = create_agent_graph()
    print(f"✅ Graph 编译成功: {graph}")
    print(f"   节点: {list(graph.nodes.keys())}")
    print(f"   边: {list(graph.edges)}")

    # 初始化状态
    ctx = AgentContext(
        uid="test_001",
        course_name="Python程序设计",
        current_phase="profile",
    )
    ctx.stamp()

    state = ctx_to_state(ctx)
    state["target_node"] = "profile"
    state["user_message"] = "我是大二学生，学过一点C语言，Python是零基础。我喜欢通过动手做项目来学习，对Web开发和数据分析比较感兴趣。"

    print("\n--- 测试 Profile Agent ---")
    print(f"输入: {state['user_message']}")
    try:
        result = graph.invoke(state)
        profile = result.get("profile_raw", "")
        print(f"画像输出: {profile[:300]}...")
        print("✅ Profile 节点运行成功")
    except Exception as e:
        print(f"❌ Profile 节点失败: {e}")
