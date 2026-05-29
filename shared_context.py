"""
=============================================================================
A3 v3 共享上下文 —— Agent 间数据模型
LangGraph 协作图的数据载体，所有 Agent 通过此模型共享信息
=============================================================================
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# 中文维度名 → 英文字段名映射（Profile Agent 输出中文 key）
_PROFILE_KEY_MAP = {
    "知识基础": "knowledge_base",
    "认知风格": "cognitive_style",
    "学习目标": "learning_goals",
    "薄弱环节": "weak_areas",
    "学习节奏": "learning_pace",
    "兴趣领域": "interests",
}
# 反向映射
_PROFILE_KEY_MAP_REV = {v: k for k, v in _PROFILE_KEY_MAP.items()}


# ============================================================================
# 基础数据类
# ============================================================================
@dataclass
class StudentProfile:
    """Step 1: 学生画像（Profile Agent 输出）"""
    knowledge_base: str = ""        # 知识基础
    cognitive_style: str = ""       # 认知风格: 视觉型/听觉型/动手型/读写型
    learning_goals: str = ""        # 学习目标
    weak_areas: str = ""            # 薄弱环节
    learning_pace: str = ""         # 学习节奏: 快速/正常/精读
    interests: str = ""             # 兴趣领域
    raw_json: str = ""              # 原始 JSON（兼容旧格式）
    updated_at: str = ""            # 更新时间

    def to_dict(self) -> dict:
        """导出为英文字段名 dict"""
        return asdict(self)

    def to_chinese_dict(self) -> dict:
        """导出为中文维度名 dict（兼容旧格式）"""
        result = {}
        for eng_key, cn_key in _PROFILE_KEY_MAP_REV.items():
            val = getattr(self, eng_key, "")
            result[cn_key] = val if val else "待了解"
        return result

    @classmethod
    def from_dict(cls, d: dict) -> "StudentProfile":
        """从 dict 创建，自动识别中/英文 key"""
        mapped = {}
        for k, v in d.items():
            if k in cls.__dataclass_fields__:
                mapped[k] = v
            elif k in _PROFILE_KEY_MAP:
                mapped[_PROFILE_KEY_MAP[k]] = v
        return cls(**{k: v for k, v in mapped.items() if k in cls.__dataclass_fields__})

    def is_complete(self) -> bool:
        """是否所有维度都已填充（非空且非"待了解"）"""
        fields = ["knowledge_base", "cognitive_style", "learning_goals",
                   "weak_areas", "learning_pace", "interests"]
        return all(getattr(self, f) and getattr(self, f) != "待了解" for f in fields)


@dataclass
class LearningResource:
    """单个学习资源"""
    title: str = ""
    source: str = ""
    url: str = ""
    desc: str = ""
    resource_type: str = ""  # 视频/实操/刷题/文档


@dataclass
class LearningResources:
    """Step 2: 学习资源（Resource Agent 输出）"""
    course_name: str = ""
    preferences: List[str] = field(default_factory=list)
    local_resources: List[dict] = field(default_factory=list)
    network_resources: List[dict] = field(default_factory=list)
    report_markdown: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LearningResources":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RoadmapStep:
    """学习路径中的单步"""
    title: str = ""
    difficulty: str = ""    # ★1-5
    estimated_time: str = ""
    objective: str = ""
    resources: List[str] = field(default_factory=list)


@dataclass
class LearningRoadmap:
    """Step 3: 学习路径（Roadmap Agent 输出）"""
    course_name: str = ""
    steps: List[dict] = field(default_factory=list)
    report_markdown: str = ""
    weakness_adjustments: List[str] = field(default_factory=list)  # 根据薄弱点做的调整
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LearningRoadmap":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WeaknessRecord:
    """单条薄弱点记录"""
    topic: str = ""                # 主题
    student_answer: str = ""       # 学生答案
    correct_answer: str = ""       # 正确答案
    diagnosis: str = ""            # 诊断（为什么会错）
    remediation: str = ""          # 补救讲解
    resources: List[str] = field(default_factory=list)  # 推荐补救资源
    path_adjustment: str = ""      # 路径调整建议
    timestamp: str = ""


@dataclass
class TutorSession:
    """Step 4: 辅导会话（Tutor Agent 输出）"""
    chat_history: List[dict] = field(default_factory=list)
    weakness_records: List[dict] = field(default_factory=list)  # List[WeaknessRecord]
    topics_covered: List[str] = field(default_factory=list)
    total_questions_asked: int = 0
    correct_count: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TutorSession":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EvaluationReport:
    """Step 5: 学习评估（Eval Agent 输出）"""
    mastery_score: int = 0         # 0-100
    progress_assessment: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    cross_validation: str = ""     # 星火交叉验证结果
    report_markdown: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvaluationReport":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================================
# 全局上下文容器 —— 所有 Agent 共享
# ============================================================================
@dataclass
class AgentContext:
    """Agent 协作的全局共享上下文

    通过 LangGraph 的 State 在各节点之间流转。
    每个节点可以读取所有字段，也可以更新自己负责的字段。
    """
    # ---- 用户标识 ----
    uid: str = ""
    course_name: str = ""

    # ---- 各 Agent 输出 ----
    profile: Optional[StudentProfile] = None
    resources: Optional[LearningResources] = None
    roadmap: Optional[LearningRoadmap] = None
    tutor_session: Optional[TutorSession] = None
    evaluation: Optional[EvaluationReport] = None

    # ---- 协作触发器 ----
    pending_weakness: bool = False      # Tutor 发现薄弱点 → 触发 Weakness Agent
    pending_eval_update: bool = False   # Weakness 完成 → 触发 Eval 更新
    pending_roadmap_adjust: bool = False  # Eval 完成 → 触发 Roadmap 调整
    pending_resource_update: bool = False  # Roadmap 调整 → 触发 Resource 更新

    # ---- 元数据 ----
    current_phase: str = "profile"     # profile | resource | roadmap | tutor | weakness | eval | done
    error_log: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        """序列化为可 JSON 存储的字典"""
        d = {}
        for k, v in asdict(self).items():
            if v is None:
                d[k] = None
            elif hasattr(v, 'to_dict'):
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AgentContext":
        """从字典反序列化"""
        ctx = cls()
        for k, v in d.items():
            if k not in cls.__dataclass_fields__:
                continue
            if v is None:
                continue
            if k == "profile" and isinstance(v, dict):
                ctx.profile = StudentProfile.from_dict(v)
            elif k == "resources" and isinstance(v, dict):
                ctx.resources = LearningResources.from_dict(v)
            elif k == "roadmap" and isinstance(v, dict):
                ctx.roadmap = LearningRoadmap.from_dict(v)
            elif k == "tutor_session" and isinstance(v, dict):
                ctx.tutor_session = TutorSession.from_dict(v)
            elif k == "evaluation" and isinstance(v, dict):
                ctx.evaluation = EvaluationReport.from_dict(v)
            else:
                setattr(ctx, k, v)
        return ctx

    def stamp(self):
        """更新时间戳"""
        now = datetime.now().isoformat()
        self.updated_at = now
        if not self.created_at:
            self.created_at = now

    def log_error(self, msg: str):
        """记录错误"""
        self.error_log.append(f"[{datetime.now().isoformat()}] {msg}")

    # ---- 协作数据查询 ----

    def get_profile_summary(self) -> str:
        """获取画像摘要（供其他 Agent 使用）"""
        if not self.profile:
            return f"课程: {self.course_name}, 画像未生成"
        p = self.profile
        lines = [
            f"课程: {self.course_name}",
            f"知识基础: {p.knowledge_base}",
            f"认知风格: {p.cognitive_style}",
            f"学习目标: {p.learning_goals}",
            f"薄弱环节: {p.weak_areas}",
            f"学习节奏: {p.learning_pace}",
            f"兴趣领域: {p.interests}",
        ]
        return "\n".join(lines)

    def get_weakness_summary(self) -> str:
        """获取薄弱点摘要（供 Roadmap/Eval 使用）"""
        if not self.tutor_session or not self.tutor_session.weakness_records:
            return "暂无薄弱点记录"
        lines = ["## 已发现的薄弱点"]
        for i, w in enumerate(self.tutor_session.weakness_records, 1):
            lines.append(f"{i}. **{w.get('topic', '未知')}** — {w.get('diagnosis', '')}")
        return "\n".join(lines)

    def has_weakness(self) -> bool:
        """是否有待处理的薄弱点"""
        return self.pending_weakness

    def has_profile(self) -> bool:
        """画像是否已生成"""
        return self.profile is not None and self.profile.is_complete()
