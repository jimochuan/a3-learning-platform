"""
=============================================================================
A3 v3 智能体 —— 六智能体协同
主力模型: 由 PRIMARY_MODEL 环境变量决定（默认 DeepSeek）
备用模型: 讯飞星火（系统预置）
多模型供应商见 providers/ 模块
=============================================================================
"""
import json
import os
import time
from typing import Optional, Dict, Any, Literal, List

from phi.agent import Agent

from providers.factory import SafeOpenAIChat, primary_model, spark_model
from providers.registry import PROVIDERS, PRIMARY_MODEL
from providers.compat import SPARK_CONFIG


# ============================================================================
# 模型工厂（薄封装）
# ============================================================================
def _primary_model(temperature: float = 0.7) -> SafeOpenAIChat:
    """主力模型：由 PRIMARY_MODEL 环境变量决定"""
    return primary_model(temperature)


def _spark_model(temperature: float = 0.7) -> SafeOpenAIChat:
    """备用模型：讯飞星火"""
    return spark_model(temperature)


def _cross_validator(temperature: float = 0.5) -> tuple:
    """交叉验证模型。返回 (模型实例, 模型名称) 或 (None, "")"""
    try:
        m = _spark_model(temperature)
        return (m, "星火")
    except Exception:
        return (None, "")


# ============================================================================
# 六智能体（主力模型均可由 PRIMARY_MODEL 切换）
# ============================================================================
class StudyAgents:
    """六智能体工厂"""

    def __init__(self, course_name: str = "", student_info: dict = None):
        self.course_name = course_name
        self.student_info = student_info or {}
        # 复用模型实例，避免每次创建 Agent 时重新连接
        self._pm = _primary_model(0.6)
        self._pm_tutor = _primary_model(0.7)
        self._pm_eval = _primary_model(0.5)
        self._pm_merge = _primary_model(0.4)

    # ---- Agent 1: 画像智能体 ----
    def profile_agent(self) -> Agent:
        system_prompt = f"""你是一位资深的教育心理学家，擅长通过对话分析学生的学习特征。

当前课程: {self.course_name}

你需要从对话中提取以下6个维度的信息:
1. 知识基础 - 学生的已有知识储备
2. 认知风格 - 视觉型/听觉型/动手型/读写型
3. 学习目标 - 短期目标（考试/项目/竞赛）和长期规划
4. 薄弱环节 - 学习中容易卡住的知识点或技能
5. 学习节奏 - 每周可投入时间 + 快速/正常/精读偏好
6. 兴趣领域 - 课程中最感兴趣的方向

规则:
- 从学生发言中客观提取，不要编造
- 未提到的维度标注"待了解"
- 输出格式: JSON，每个维度一句话总结"""
        return Agent(model=self._pm, system_prompt=system_prompt)

    # ---- Agent 2: 资源生成智能体 ----
    def resource_agent(self) -> Agent:
        system_prompt = f"""你是一位经验丰富的课程设计师，擅长根据学生画像生成个性化学习资源。

当前课程: {self.course_name}

你需要生成以下4种资源:
1. 课程讲解文档 - 系统性知识点讲解，含比喻和总结
2. 练习题目 - 3选择+2简答+1综合，标注难度星级
3. 拓展阅读 - 推荐论文/书籍/开源项目/课程
4. 代码实操 - 完整可运行代码 + 中文注释 + 动手实验

个性化要求:
- 根据学生知识基础调整深度
- 匹配学生的认知风格
- 针对薄弱环节加提示
- 内容难度匹配学习节奏

输出使用Markdown格式。"""
        return Agent(model=self._pm_tutor, system_prompt=system_prompt)

    # ---- Agent 3: 路径规划智能体 ----
    def roadmap_agent(self) -> Agent:
        system_prompt = f"""你是一位资深的学习路径设计师。

当前课程: {self.course_name}

规划5-8步个性化学习路径（精简高效）。

每条路径步骤需包含:
- 步骤标题
- 难度(★1-5)
- 预估时间
- 学习目标(一句话)
- 推荐资源(1-2个)

路径原则: 从易到难，关键节点设检查点，针对薄弱环节加强。

输出Markdown表格格式。"""
        return Agent(model=self._pm_tutor, system_prompt=system_prompt)

    # ---- Agent 4: 智能辅导 + 双向互动智能体 ----
    def tutor_agent(self) -> Agent:
        system_prompt = f"""你是一位耐心专业的辅导老师，同时能测试学生的学习效果。

当前课程: {self.course_name}

你有两种互动模式，在对话中自然切换:

【讲解模式】
- 学生提问 → 你按照"1.概念概述 2.详细讲解 3.生活化例子 4.练习建议 5.延伸思考题"结构回答
- 讲解结束后，可以问一句"要不要测一下你对这个知识点的理解？"（学生可以拒绝）
- 学生说"不了"/"不用"/"算了"就不追问，继续正常对话
- 不要每轮都问，如果上一轮刚问过就别再问

【测验模式】学生同意或主动要求测试时进入:
- 出1-2道跟刚才话题直接相关的题（概念理解/场景应用/简答）
- 题目不要太难，目的是验证理解而非刁难
- 学生回答后必须判断对错:
  · 答对 → 肯定鼓励（1句话），然后简短总结为什么对
  · 答错/不会 → 先告知正确答案（1-2句），然后输出 [WEAKNESS:主题|学生答案|正确答案]
- 学生主动说"考考我"/"测一下"/"来道题"也可以进入测验

关键规则:
- 学生说"不了"必须尊重，绝不追问
- 测验题必须跟刚讨论的内容相关，不跑题
- 始终保持鼓励态度"""
        return Agent(model=self._pm_tutor, system_prompt=system_prompt)

    # ---- Agent 4b: 薄弱点分析智能体 ----
    def weakness_agent(self) -> Agent:
        """答错时分析薄弱点，生成补充资源和路径调整建议"""
        system_prompt = f"""你是一位学习诊断专家，擅长分析学生的知识薄弱点并制定补救方案。

当前课程: {self.course_name}

当学生在测验中答错时，你需要:
1. 诊断学生为什么会错（概念混淆/理解不深/完全不会/记错了）
2. 生成针对性的补充讲解（用更简单的方式重新讲一遍）
3. 推荐1-2个具体的学习资源（类型: 视频/文章/练习/代码实操）
4. 指出当前学习路径中哪一步需要加强

输出Markdown格式:
## 薄弱点诊断
（1-2句分析为什么会错）

## 补充讲解
（用不同角度重新讲解，更通俗）

## 推荐补救资源
- 资源1: xxx
- 资源2: xxx

## 路径调整建议
（指出学习路径中需要加强的步骤）"""
        return Agent(model=self._pm_eval, system_prompt=system_prompt)

    # ---- Agent 5: 学习评估智能体 ----
    def eval_agent(self) -> Agent:
        system_prompt = f"""你是一位专业的学习效果评估专家。

当前课程: {self.course_name}

根据学生学习数据，生成评估报告:
1. 知识掌握度评分 (0-100)
2. 学习进度评估
3. 优势领域分析
4. 薄弱环节诊断
5. 下一步学习建议

客观公正，给出具体可操作建议。输出Markdown格式。"""
        return Agent(model=self._pm_eval, system_prompt=system_prompt)

    # ---- Agent 6: RAG辅导智能体（基于文档） ----
    def rag_tutor_agent(self) -> Agent:
        system_prompt = """你是一位基于教材资料的辅导老师。

重要规则:
- 回答必须基于提供的文档内容
- 文档中没有的信息，明确说"资料中未涉及此内容"
- 引用时标注具体章节或页码
- 用学生能理解的语言解释
- 遇到不确定的不编造"""
        return Agent(model=self._pm, system_prompt=system_prompt)

    # ---- 交叉验证评估（星火） ----
    def cross_validator_agent(self) -> tuple:
        model, name = _cross_validator(0.5)
        if model is None:
            return (None, "")
        system_prompt = f"""你是一位专业的学习效果评估专家（交叉校验角色）。

当前课程: {self.course_name}

独立评估学生学习数据:
1. 知识掌握度评分 (0-100)
2. 学习进度评估
3. 优势领域分析
4. 薄弱环节诊断
5. 下一步学习建议

客观公正，输出Markdown格式。"""
        return (Agent(model=model, system_prompt=system_prompt), name)

    # ---- 交叉验证 ----
    def cross_validate(self, eval_data: str) -> dict:
        result = {"glm": None, "spark": None, "spark_label": "星火", "merged": None}

        glm_agent = self.eval_agent()
        result["glm"], _ = run_with_fallback(glm_agent, eval_data)

        spark_agent, spark_name = self.cross_validator_agent()
        if spark_agent is not None:
            try:
                result["spark"] = spark_agent.run(eval_data).content
            except Exception:
                result["spark"] = "(星火暂时不可用)"
            result["spark_label"] = spark_name
            result["merged"] = self._merge_evals(
                result["glm"], result["spark"], spark_name
            )
        else:
            result["merged"] = result["glm"]

        return result

    def _merge_evals(self, main_eval: str, spark_eval: str, spark_name: str) -> str:
        merge_prompt = f"""融合以下两份评估报告，生成最终综合评估。
规则: 一致结论保留, 评分取平均, 分歧标注"双模型存在分歧"并列观点, 建议取并集。

=== 主模型评估报告 ===
{main_eval}

=== {spark_name} 评估报告 ===
{spark_eval}

输出融合后综合评估报告，Markdown格式。"""
        merger = Agent(model=self._pm_merge, system_prompt="你是评估仲裁专家。")
        merged, _ = run_with_fallback(merger, merge_prompt)
        return merged


# ============================================================================
# 便捷函数
# ============================================================================
def create_agents(course_name: str = "", student_info: dict = None) -> StudyAgents:
    """创建六智能体工厂"""
    return StudyAgents(course_name=course_name, student_info=student_info)


def run_with_fallback(primary_agent: Agent, prompt: str, max_retries: int = 2):
    """带重试和降级的 agent.run() 封装

    先尝试主力模型（PRIMARY_MODEL），重试 max_retries 次。
    全部失败后降级到星火。

    返回 (response_content: str, model_label: str)
    """
    label = PROVIDERS.get(PRIMARY_MODEL, {}).get("label", "主力模型")
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = primary_agent.run(prompt, stream=False)
            return (resp.content, label)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(1)

    # 降级到星火
    try:
        spark = _spark_model(0.5)
        fallback = Agent(model=spark, system_prompt=primary_agent.system_prompt)
        resp = fallback.run(prompt, stream=False)
        return (resp.content, "星火(备用)")
    except Exception:
        pass

    raise last_error


def stream_chat(primary_agent: Agent, prompt: str):
    """流式输出，带降级。逐段 yield 文本内容。"""
    last_error = None
    for attempt in range(2):
        try:
            for chunk in primary_agent.run(prompt, stream=True):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    yield content
            return
        except Exception as e:
            last_error = e
            if attempt < 1:
                time.sleep(1)

    # 降级到星火
    try:
        spark = _spark_model(0.5)
        fallback = Agent(model=spark, system_prompt=primary_agent.system_prompt)
        for chunk in fallback.run(prompt, stream=True):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                yield content
    except Exception:
        raise last_error
