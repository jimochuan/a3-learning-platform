"""
=============================================================================
对话式学习偏好提取 + 本地库兜底 + 模拟联网补充
个性化资源推荐智能体 —— DialogueResourceAgent
=============================================================================
用于 Step 2: 通过多轮对话提取学习偏好，查询双层资源体系生成推荐
无外部依赖，可直接运行
=============================================================================
"""
import re
import json
from typing import Dict, List, Optional, Tuple


# ============================================================================
# 本地课程-偏好资源库（兜底层）
# 结构: {课程: {偏好类型: [资源列表]}}
# 偏好类型: 视频 | 实操 | 刷题 | 文档
# ============================================================================
LOCAL_RESOURCE_DB: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "C语言": {
        "视频": [
            {"title": "浙大翁恺《C语言程序设计》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/ZJU-1001614008", "desc": "国家级精品课，零基础友好，翁恺老师讲解生动"},
            {"title": "B站《C语言从入门到精通》2025版", "source": "B站", "url": "https://www.bilibili.com/video/BV1qF411n7gx", "desc": "120集系统教程，每集15分钟，配套习题和源码"},
            {"title": "郝斌《C语言自学教程》", "source": "B站", "url": "https://www.bilibili.com/video/BV1os411h7zL", "desc": "180集经典教程，讲解细致适合零基础"},
        ],
        "实操": [
            {"title": "C语言经典100题实训", "source": "GitHub", "url": "https://github.com/gouhuacheng/C-language-100-cases", "desc": "100道经典编程题从易到难，每道题配多种解法"},
            {"title": "学生信息管理系统（C语言小项目）", "source": "GitHub", "url": "https://github.com/topics/student-management-c", "desc": "链表+文件操作实战，适合学完语法后练习"},
            {"title": "C语言贪吃蛇游戏开发", "source": "GitHub", "url": "https://github.com/topics/snake-game-c", "desc": "控制台贪吃蛇，综合练习数组、函数、结构体"},
        ],
        "刷题": [
            {"title": "LeetCode C语言分类练习", "source": "LeetCode", "url": "https://leetcode.cn/problemset/all/?languageTags=c", "desc": "按数据结构分类刷题，从简单到困难循序渐进"},
            {"title": "PTA程序设计类实验辅助教学平台", "source": "PTA", "url": "https://pintia.cn/problem-sets", "desc": "浙大PAT真题+基础编程题目集，含自动评测"},
            {"title": "牛客网C语言专项练习", "source": "牛客网", "url": "https://www.nowcoder.com/exam/oj?tab=C%E8%AF%AD%E8%A8%80", "desc": "选择题+编程题混合，覆盖指针/内存等易错点"},
        ],
        "文档": [
            {"title": "《C Primer Plus》第6版 中文版", "source": "人民邮电出版社", "url": "", "desc": "C语言经典教材，近800页系统讲解，每章附复习题"},
            {"title": "《C程序设计语言》K&R 经典", "source": "机械工业出版社", "url": "", "desc": "C语言之父所著，精炼深刻，适合有基础后精读"},
            {"title": "C语言标准库速查手册(cppreference)", "source": "cppreference.com", "url": "https://zh.cppreference.com/w/c", "desc": "标准库函数在线速查，包含示例代码"},
        ],
    },
    "Python": {
        "视频": [
            {"title": "北京理工《Python语言程序设计》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/BIT-268001", "desc": "嵩天老师主讲，国家级精品课，零基础入门首选"},
            {"title": "B站《Python全套教程》黑马程序员2025版", "source": "B站", "url": "https://www.bilibili.com/video/BV1qW4y1a7fU", "desc": "600集从入门到就业，每集有笔记和代码"},
        ],
        "实操": [
            {"title": "Python爬虫实战：豆瓣电影Top250", "source": "GitHub", "url": "https://github.com/topics/douban-spider", "desc": "requests+BeautifulSoup实战，数据保存CSV"},
            {"title": "Flask博客系统从零搭建", "source": "GitHub", "url": "https://github.com/topics/flask-blog", "desc": "Python Web全栈练习，含用户注册/文章管理/评论"},
        ],
        "刷题": [
            {"title": "LeetCode Hot 100 Python题解", "source": "LeetCode", "url": "https://leetcode.cn/problemset/all/?languageTags=python3", "desc": "高频面试题Python版，含多种解法对比"},
            {"title": "蓝桥杯Python组真题训练", "source": "蓝桥杯官网", "url": "https://www.lanqiao.cn/problems/", "desc": "竞赛级算法题，适合进阶练习"},
        ],
        "文档": [
            {"title": "《Python编程：从入门到实践》第3版", "source": "人民邮电出版社", "url": "", "desc": "项目驱动式学习，含外星人入侵游戏+Django Web项目"},
            {"title": "Python官方中文文档", "source": "python.org", "url": "https://docs.python.org/zh-cn/3/", "desc": "最权威的参考文档，含标准库完整说明"},
        ],
    },
    "机械控制原理": {
        "视频": [
            {"title": "哈工大《自动控制原理》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/HIT-1001515002", "desc": "控制理论核心课程，频域/时域分析系统讲解"},
            {"title": "B站《机械控制工程基础》", "source": "B站", "url": "https://www.bilibili.com/video/BV1AW411d7Bp", "desc": "拉普拉斯变换→传递函数→稳定性分析，由浅入深"},
        ],
        "实操": [
            {"title": "MATLAB控制系统仿真实验", "source": "MathWorks", "url": "https://www.mathworks.com/products/control.html", "desc": "PID调参/根轨迹/Bode图仿真，附带Simulink模型"},
            {"title": "基于Arduino的PID温控系统", "source": "GitHub", "url": "https://github.com/topics/pid-arduino", "desc": "实物控制项目，从理论到实践理解PID"},
        ],
        "刷题": [
            {"title": "自动控制原理考研真题集", "source": "考研论坛", "url": "", "desc": "各大高校历年真题，含详细解析和答案"},
            {"title": "控制工程基础习题精解", "source": "高等教育出版社", "url": "", "desc": "配套《机械控制工程基础》课后习题详解"},
        ],
        "文档": [
            {"title": "《自动控制原理》胡寿松 第7版", "source": "科学出版社", "url": "", "desc": "国内控制理论权威教材，考研指定参考书"},
            {"title": "《Modern Control Engineering》Ogata", "source": "Pearson", "url": "", "desc": "国际经典教材，英文原版，MATLAB案例丰富"},
        ],
    },
    "单片机原理": {
        "视频": [
            {"title": "郭天祥《十天学会51单片机》", "source": "B站", "url": "https://www.bilibili.com/video/BV1MW411q7Jn", "desc": "经典入门教程，手把手教从点亮LED到串口通信"},
            {"title": "正点原子《STM32入门到精通》", "source": "B站", "url": "https://www.bilibili.com/video/BV1kx411k7JT", "desc": "STM32F1/F4系列全套教程，含HAL库开发"},
        ],
        "实操": [
            {"title": "51单片机电子钟制作", "source": "GitHub", "url": "https://github.com/topics/51-clock", "desc": "数码管显示+定时器+按键扫描综合项目"},
            {"title": "STM32智能小车项目", "source": "GitHub", "url": "https://github.com/topics/stm32-car", "desc": "PWM调速/超声波避障/蓝牙遥控全栈项目"},
        ],
        "刷题": [
            {"title": "单片机原理与应用习题集", "source": "电子工业出版社", "url": "", "desc": "按章节分类：IO/中断/定时器/串口/ADC各50题"},
            {"title": "蓝桥杯嵌入式设计与开发真题", "source": "蓝桥杯官网", "url": "https://www.lanqiao.cn/problems/", "desc": "STM32GD平台竞赛真题，含官方评测标准"},
        ],
        "文档": [
            {"title": "《手把手教你学51单片机》宋雪松", "source": "清华大学出版社", "url": "", "desc": "全彩印刷+实物图，适合零基础自学"},
            {"title": "STM32中文参考手册", "source": "意法半导体", "url": "https://www.st.com/zh/microcontrollers-microprocessors/stm32f1-series.html", "desc": "官方寄存器/库函数完整说明，开发必备"},
        ],
    },
    "机械设计": {
        "视频": [
            {"title": "西北工业《机械设计》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/NWPU-1001552015", "desc": "齿轮/轴/轴承/联轴器系统讲解，含工程案例"},
            {"title": "B站《SolidWorks机械设计实战》", "source": "B站", "url": "https://www.bilibili.com/video/BV1GJ411x7De", "desc": "从草图绘制到装配体出图，30个实战案例"},
        ],
        "实操": [
            {"title": "减速器设计完整流程", "source": "机械设计课程设计", "url": "", "desc": "一级/二级圆柱齿轮减速器设计计算+CAD出图"},
            {"title": "SolidWorks零件建模100例", "source": "B站", "url": "https://www.bilibili.com/video/BV1i54y1y7Xc", "desc": "从简单轴套到复杂箱体逐步练习"},
        ],
        "刷题": [
            {"title": "机械设计考研真题精选", "source": "考研论坛", "url": "", "desc": "齿轮强度计算/轴承寿命/键连接校核高频考题"},
            {"title": "《机械设计》课后习题全解", "source": "高等教育出版社", "url": "", "desc": "濮良贵版教材配套，每章详细解题步骤"},
        ],
        "文档": [
            {"title": "《机械设计》濮良贵 第10版", "source": "高等教育出版社", "url": "", "desc": "国内机械专业权威教材，考研指定参考书"},
            {"title": "《Shigley's Mechanical Engineering Design》", "source": "McGraw-Hill", "url": "", "desc": "国际机械设计圣经，含英制/公制双版本计算"},
        ],
    },
    "数据结构": {
        "视频": [
            {"title": "浙大陈越《数据结构》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/ZJU-93001", "desc": "国精品课，何钦铭/陈越讲链表/树/图/排序"},
            {"title": "B站《代码随想录》算法公开课", "source": "B站", "url": "https://www.bilibili.com/video/BV1fA4y1o7yU", "desc": "LeetCode刷题方法论，含动图演示和代码"},
        ],
        "实操": [
            {"title": "数据结构可视化练习", "source": "visualgo.net", "url": "https://visualgo.net/zh", "desc": "22种数据结构动态可视化，支持自己动手建树/走图"},
            {"title": "手写红黑树/AVL树（C++实现）", "source": "GitHub", "url": "https://github.com/topics/red-black-tree", "desc": "平衡树完整实现，含详细中文注释"},
        ],
        "刷题": [
            {"title": "LeetCode 数据结构专题", "source": "LeetCode", "url": "https://leetcode.cn/studyplan/data-structures/", "desc": "数组/链表/栈/队列/树/图分专题系统刷题"},
            {"title": "《剑指Offer》数据结构题目精讲", "source": "牛客网", "url": "https://www.nowcoder.com/exam/oj?tab=%E5%89%91%E6%8C%87Offer", "desc": "面试高频数据结构题，含最优解和多语言实现"},
        ],
        "文档": [
            {"title": "《数据结构（C语言版）》严蔚敏", "source": "清华大学出版社", "url": "", "desc": "国内数据结构经典教材，考研指定参考书"},
            {"title": "《算法导论》CLRS 第4版", "source": "MIT Press", "url": "", "desc": "算法领域圣经，深入理解数据结构和算法分析"},
        ],
    },
    "模电/数电": {
        "视频": [
            {"title": "清华《模拟电子技术基础》MOOC", "source": "学堂在线", "url": "https://www.xuetangx.com/course/THU08011000028", "desc": "华成英老师主讲，二极管/三极管/运放系统讲解"},
            {"title": "B站《数字电子技术基础》", "source": "B站", "url": "https://www.bilibili.com/video/BV1kE411w7Fm", "desc": "逻辑门→组合电路→时序电路→AD/DA转换"},
        ],
        "实操": [
            {"title": "Multisim模电仿真实验合集", "source": "NI", "url": "https://www.multisim.com/", "desc": "共射放大/差分放大/运放电路在线仿真"},
            {"title": "FPGA数电实验：交通灯控制器", "source": "GitHub", "url": "https://github.com/topics/traffic-light-fpga", "desc": "Verilog实现状态机控制交通灯"},
        ],
        "刷题": [
            {"title": "《模拟电子技术基础》课后习题详解", "source": "高等教育出版社", "url": "", "desc": "童诗白版教材配套，每章30+题含详细解答"},
            {"title": "数电逻辑设计题库500题", "source": "电子工业出版社", "url": "", "desc": "卡诺图化简/组合逻辑设计/触发器应用分类训练"},
        ],
        "文档": [
            {"title": "《模拟电子技术基础》童诗白 第5版", "source": "高等教育出版社", "url": "", "desc": "国内模电经典教材，电路分析+设计方法并重"},
            {"title": "《数字电子技术基础》阎石 第6版", "source": "高等教育出版社", "url": "", "desc": "数电权威教材，CMOS/TTL电路到可编程逻辑"},
        ],
    },
    "高等数学": {
        "视频": [
            {"title": "MIT《单变量微积分》公开课", "source": "MIT OCW", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus", "desc": "Gilbert Strang教授主讲，强调直觉理解而非公式"},
            {"title": "B站《高等数学》宋浩老师全集", "source": "B站", "url": "https://www.bilibili.com/video/BV1Et411j7Mz", "desc": "幽默风趣，从极限到多重积分全覆盖"},
        ],
        "实操": [
            {"title": "Python符号计算练高数", "source": "GitHub", "url": "https://github.com/topics/sympy-calculus", "desc": "用SymPy求极限/导数/积分/级数，可视化理解概念"},
            {"title": "MATLAB数学实验", "source": "MathWorks", "url": "https://www.mathworks.com/products/matlab.html", "desc": "3D曲面绘制/梯度场/泰勒展开可视化实验"},
        ],
        "刷题": [
            {"title": "《高等数学习题全解指南》同济版配套", "source": "高等教育出版社", "url": "", "desc": "同济七版教材课后习题标准答案+解题思路"},
            {"title": "考研数学一真题高数部分", "source": "考研论坛", "url": "", "desc": "1987-2025年真题分类汇编，按章节可筛选"},
        ],
        "文档": [
            {"title": "《高等数学》同济大学 第7版", "source": "高等教育出版社", "url": "", "desc": "国内高数经典教材，考研数学指定参考书"},
            {"title": "《普林斯顿微积分读本》", "source": "人民邮电出版社", "url": "", "desc": "口语化讲解微积分本质，适合想真正理解的人"},
        ],
    },
    "人工智能导论": {
        "视频": [
            {"title": "吴恩达《机器学习》Coursera 中文版", "source": "Coursera/B站", "url": "https://www.bilibili.com/video/BV164411b7dx", "desc": "AI入门首选课程，从线性回归到神经网络，讲解清晰直观"},
            {"title": "李宏毅《机器学习》2025 深度学习导论", "source": "B站", "url": "https://www.bilibili.com/video/BV1TD4y137mP", "desc": "台湾大学王牌课程，国语授课，动画丰富理解直观"},
            {"title": "Stanford CS229《机器学习》吴恩达", "source": "Stanford/YouTube", "url": "https://www.youtube.com/playlist?list=PLoROMvodv4rMiGQp3Wlht2Kk", "desc": "机器学习理论经典，推导详实，适合深入学习"},
        ],
        "实操": [
            {"title": "Kaggle Titanic 入门竞赛", "source": "Kaggle", "url": "https://www.kaggle.com/c/titanic", "desc": "经典ML入门项目，数据清洗→特征工程→模型训练全流程"},
            {"title": "TensorFlow 官方 MNIST 手写数字识别", "source": "TensorFlow", "url": "https://www.tensorflow.org/tutorials/quickstart/beginner", "desc": "官方入门教程，构建CNN识别手写数字，含完整代码"},
            {"title": "scikit-learn 中文文档与示例", "source": "scikit-learn", "url": "https://scikit-learn.org.cn/", "desc": "Python ML标准库的中文文档，每个算法都有可运行示例"},
        ],
        "刷题": [
            {"title": "LeetCode 机器学习专项", "source": "LeetCode", "url": "https://leetcode.cn/problemset/machine-learning/", "desc": "ML算法实现题，从线性回归到K-Means手写"},
            {"title": "牛客网 AI 面试题库", "source": "牛客网", "url": "https://www.nowcoder.com/exam/oj?tab=AI%E9%9D%A2%E8%AF%95", "desc": "大厂AI岗面试真题，含ML/DL/NLP/CV各方向"},
        ],
        "文档": [
            {"title": "《机器学习》周志华（西瓜书）", "source": "清华大学出版社", "url": "", "desc": "国内ML经典教材，公式推导清晰，配套南瓜书逐公式解读"},
            {"title": "《深度学习》Ian Goodfellow（花书）", "source": "MIT Press", "url": "https://www.deeplearningbook.org/", "desc": "深度学习领域圣经，适合有ML基础后精读"},
        ],
    },
    "计算机网络": {
        "视频": [
            {"title": "哈工大《计算机网络》MOOC", "source": "中国大学MOOC", "url": "https://www.icourse163.org/course/HIT-154005", "desc": "李全龙老师主讲，TCP/IP协议栈逐层讲解"},
            {"title": "B站《计算机网络微课堂》湖科大教书匠", "source": "B站", "url": "https://www.bilibili.com/video/BV1c4411d7jb", "desc": "动画演示+实操抓包，200集系统讲解从物理层到应用层"},
            {"title": "Stanford CS144《计算机网络》", "source": "Stanford", "url": "https://cs144.github.io/", "desc": "经典课程，TCP实现实验 + 协议设计思维"},
        ],
        "实操": [
            {"title": "Wireshark 抓包实验", "source": "Wireshark", "url": "https://www.wireshark.org/", "desc": "捕获分析TCP三次握手/四次挥手/HTTP/HTTPS流量"},
            {"title": "Python Socket 网络编程实战", "source": "GitHub", "url": "https://github.com/topics/python-socket", "desc": "手写HTTP服务器/聊天程序/P2P文件传输"},
        ],
        "刷题": [
            {"title": "计算机网络考研408真题", "source": "考研论坛", "url": "", "desc": "1987-2025年408统考真题，TCP/IP重点章节精讲"},
            {"title": "华为/思科 HCIA/CCNA 认证题库", "source": "华为/思科", "url": "", "desc": "企业级网络认证题库，含子网划分/VLAN/路由协议实操题"},
        ],
        "文档": [
            {"title": "《计算机网络：自顶向下方法》第8版", "source": "机械工业出版社", "url": "", "desc": "全球最流行计网教材，从应用层向下讲解，案例丰富"},
            {"title": "《TCP/IP详解 卷1：协议》", "source": "机械工业出版社", "url": "", "desc": "网络协议圣经，深度剖析TCP/IP各层协议细节"},
        ],
    },
}


# ============================================================================
# 关键词词典：用于从自然语言中提取偏好信息
# ============================================================================
PREFERENCE_KEYWORDS = {
    "视频": ["看视频", "视频", "b站", "mooc", "慕课", "网课", "听课", "上课", "课程视频", "教学视频", "录播", "直播课", "公开课", "在线课程"],
    "实操": ["动手", "实操", "写代码", "敲代码", "编程", "做项目", "实践", "实验", "操作", "上机", "debug", "调试", "跑代码", "做东西", "实战"],
    "刷题": ["刷题", "做题", "练习", "习题", "考试", "测验", "题库", "考试题", "题目", "leet", "牛客", "pta", "oj"],
    "文档": ["看书", "读书", "阅读", "文档", "书籍", "教材", "课本", "参考书", "手冊", "手册", "笔记", "博客", "文章", "paper", "论文", "报纸"],
}

PACE_KEYWORDS = {
    "快速": ["快速", "快节奏", "倍速", "跳着看", "快点", "赶时间", "粗略浏览", "过一遍", "速通", "速成", "突击", "几天搞定", "短时间"],
    "正常": ["正常", "一般", "适中", "普通", "常规", "平常"],
    "精读": ["慢慢", "仔细", "精读", "研读", "深入", "深耕", "扎实", "透彻", "慢一点", "稳稳", "慢慢来", "好好学", "深究", "认真", "细嚼慢咽"],
}

BASIS_KEYWORDS = {
    "零基础": ["零基础", "没学过", "没有基础", "完全不会", "一点都不会", "刚开始", "刚接触", "还没学", "不会", "小白", "新手", "门外汉", "什么都不知道",
              "下学期才", "准备开始", "不了解", "没接触过", "不知道", "没了解", "没有诶", "才开始"],
    "入门": ["学过一点", "学过一些", "有点基础", "入门", "了解一点", "了解一些", "了解过", "接触过", "刚学完", "学了一些", "基本语法", "简单代码", "皮毛", "大概了解",
            "能写简单", "会点", "懂一点", "有点了解", "基础差", "基础不好", "基础薄弱", "底子差", "基础比较差", "比较薄弱", "比较差", "学得不好", "不太会", "比较弱"],
    "熟练": ["学过", "能写", "做过项目", "有基础", "比较熟", "用过", "掌握", "熟悉", "独立完成", "学完了", "做过的", "能独立", "比较了解"],
    "精通": ["精通", "很熟", "很懂", "深入理解", "源码级", "专家", "多年经验", "深层次", "很熟练", "深入的", "透彻理解"],
}


# ============================================================================
# DialogueResourceAgent —— 核心类
# ============================================================================
class DialogueResourceAgent:
    """对话式学习偏好提取 + 本地库兜底 + 模拟联网补充 智能体"""

    def __init__(self, course_name: str = "", profile: dict = None):
        """
        初始化智能体
        Args:
            course_name: 课程名称（从 Step 1 画像获取）
            profile: Step 1 生成的学生画像
        """
        self.course_name = course_name
        self.profile = profile or {}

        # 从 profile 中提取可能已含的信息
        self.extracted = {
            "course": course_name,
            "basis": self.profile.get("知识基础", ""),
            "preferences": [],      # 学习偏好（可多选）
            "pace": "",             # 学习节奏
            "goals": self.profile.get("学习目标", ""),
            "weakness": self.profile.get("薄弱环节", ""),
        }

        # ---- 从 Step 1 profile 预填充偏好 / 节奏 / 基础（避免 Step 2 重复问） ----
        self._prefill_from_profile()

        # 多轮对话状态
        self.dialogue_round = 0
        self.dialogue_history: List[Dict[str, str]] = []

        # 预定义对话问题（根据已有画像自适应调整）
        self.questions = self._build_questions()

    # ---- 认知风格 → 学习偏好映射 ----
    STYLE_TO_PREFERENCE = {
        "视觉型": "视频",
        "听觉型": "视频",   # 听课 / 播客 → 视频类资源最接近
        "动手型": "实操",
        "读写型": "文档",
    }

    def _prefill_from_profile(self):
        """从 Step 1 画像预填充已确定的偏好信息，避免 Step 2 重复询问"""
        style = self.profile.get("认知风格", "")
        if style and style != "待了解":
            pref = self.STYLE_TO_PREFERENCE.get(style, "")
            if pref and pref not in self.extracted["preferences"]:
                self.extracted["preferences"].append(pref)

        pace = self.profile.get("学习节奏", "")
        if pace and pace != "待了解" and not self.extracted["pace"]:
            self.extracted["pace"] = pace

        basis = self.profile.get("知识基础", "")
        if basis and basis != "待了解" and not self.extracted["basis"]:
            self.extracted["basis"] = basis

    def _build_questions(self) -> List[str]:
        """根据 Step 1 画像构建需要追问的问题列表

        Step 1 已覆盖的维度自动跳过，不再重复询问。
        """
        questions = []

        # Q1: 确认课程（如果未知）
        if not self.course_name or self.course_name == "待了解":
            questions.append("你想学习哪门课程呢？比如C语言、Python、数据结构、高等数学等～")

        # Q2: 了解基础（如果画像中未填）
        if not self.extracted["basis"] or self.extracted["basis"] == "待了解":
            questions.append(f"你对{'这门课' if self.course_name else '想学的课程'}有什么基础了解吗？比如之前学过一点、完全零基础、还是已经能独立做项目了？")

        # Q3: 学习方式偏好 —— 仅当 Step 1 未确定认知风格时才问
        style = self.profile.get("认知风格", "")
        if not style or style == "待了解":
            questions.append("你更喜欢通过哪种方式来学习呢？喜欢看视频跟着学、还是自己动手写代码/做实验、还是喜欢刷题巩固、或者看书读文档？")
        elif not self.extracted["preferences"]:
            # 认知风格已知但映射失败（极端情况）→ 追问
            questions.append("你更喜欢通过哪种方式来学习呢？喜欢看视频跟着学、还是自己动手写代码/做实验、还是喜欢刷题巩固、或者看书读文档？")

        # Q4: 学习节奏 —— 仅当 Step 1 未确定时才问
        if not self.extracted["pace"] or self.extracted["pace"] == "待了解":
            questions.append("你平时学习喜欢快速浏览过一遍、按照正常节奏、还是仔细研读每个细节呢？")

        return questions

    # ------------------------------------------------------------------
    # 方法1: 关键词自动提取
    # ------------------------------------------------------------------
    def extract_keywords(self, user_input: str) -> Dict[str, any]:
        """
        从用户自然语言回答中提取关键词
        Args:
            user_input: 用户的一句话回答
        Returns:
            提取到的结构化信息
        """
        text = user_input.strip()
        result = {
            "course": "",
            "basis": "",
            "preferences": [],
            "pace": "",
        }

        # --- 提取课程名称 ---
        known_courses = list(LOCAL_RESOURCE_DB.keys())
        for course in known_courses:
            # 支持模糊匹配：C语言/C/c语言
            if course.lower() == "c语言":
                if re.search(r"[Cc]语言|[Cc](?:\s|$|语言|编程|，|。|！|\.)", text):
                    result["course"] = course
                    break
            elif course.lower() in text.lower():
                result["course"] = course
                break
        # 如果能从 profile 中获取，使用 profile 中的课程
        if not result["course"] and self.course_name:
            result["course"] = self.course_name

        # --- 否定检测（共用） ---
        PREF_NEGATION_MARKERS = ["不是", "不算", "并非", "算不上", "没有", "不是个", "不能算",
                                 "不喜欢", "不爱", "不咋", "不怎么", "不太喜欢", "不习惯",
                                 "讨厌", "烦", "受不了"]
        PACE_NEGATION_MARKERS = ["不是", "不算", "并非", "算不上", "没有", "不是个", "不能算",
                                 "不喜欢", "不想", "不想要", "不需要", "没必要", "不用"]

        def _is_negated(text, pos, markers):
            """检查关键词位置 pos 之前 5 个字符内是否有否定标记"""
            prefix = text[max(0, pos - 5):pos]
            return any(neg in prefix for neg in markers)

        # --- 提取学习基础 ---
        BASIS_NEGATION_MARKERS = ["不是", "不算", "并非", "算不上", "没有", "不是个", "不能算"]
        for level, keywords in BASIS_KEYWORDS.items():
            for kw in keywords:
                pos = text.find(kw)
                if pos >= 0:
                    if not _is_negated(text, pos, BASIS_NEGATION_MARKERS):
                        result["basis"] = level
                        break
            if result["basis"]:
                break
        # 如果已知知识基础，用已知的
        if not result["basis"] and self.extracted["basis"] and self.extracted["basis"] != "待了解":
            result["basis"] = self.extracted["basis"]

        # --- 提取学习偏好（可多选，支持否定检测） ---
        for pref_type, keywords in PREFERENCE_KEYWORDS.items():
            for kw in keywords:
                pos = text.find(kw)
                if pos >= 0:
                    if not _is_negated(text, pos, PREF_NEGATION_MARKERS):
                        if pref_type not in result["preferences"]:
                            result["preferences"].append(pref_type)
                        break

        # --- 提取学习节奏（支持否定检测） ---
        for pace_type, keywords in PACE_KEYWORDS.items():
            for kw in keywords:
                pos = text.find(kw)
                if pos >= 0:
                    if not _is_negated(text, pos, PACE_NEGATION_MARKERS):
                        result["pace"] = pace_type
                        break
            if result["pace"]:
                break

        return result

    # 课程名映射：config.py 中的课程名 → LOCAL_RESOURCE_DB 的键名
    COURSE_ALIASES = {
        "Python程序设计": "Python",
        "数据结构与算法": "数据结构",
    }

    # ------------------------------------------------------------------
    # 方法2: 本地资源库查询
    # ------------------------------------------------------------------
    def local_resource_query(self, course: str, preferences: List[str]) -> List[Dict[str, str]]:
        """
        查询本地内置课程-偏好资源库
        Args:
            course: 课程名称
            preferences: 学习偏好列表，如 ["视频", "实操"]
        Returns:
            本地资源列表
        """
        # 映射 config.py 的课程名到本地库的键名
        db_course = self.COURSE_ALIASES.get(course, course)
        if db_course not in LOCAL_RESOURCE_DB:
            # 课程不在库中，返回通用推荐
            return [
                {"title": f"B站搜索「{course}」热门教程", "source": "B站", "url": f"https://search.bilibili.com/all?keyword={course}",
                 "desc": f"在B站搜索{course}相关教程，筛选播放量高的视频"},
                {"title": f"GitHub搜索「{course}」开源项目", "source": "GitHub", "url": f"https://github.com/search?q={course}",
                 "desc": f"在GitHub搜索{course}相关项目，按Star数排序"},
            ]

        course_db = LOCAL_RESOURCE_DB[db_course]
        results = []

        # 按用户偏好优先级取资源
        if preferences:
            for pref in preferences:
                if pref in course_db:
                    # 每种偏好取前2个资源
                    results.extend(course_db[pref][:2])
        else:
            # 没有明确偏好，每种类型各取1个
            for pref_type in ["文档", "视频", "实操", "刷题"]:
                if pref_type in course_db and course_db[pref_type]:
                    results.append(course_db[pref_type][0])

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r["title"] not in seen:
                seen.add(r["title"])
                unique_results.append(r)

        return unique_results[:6]  # 最多6个本地资源

    # ------------------------------------------------------------------
    # 方法3: 模拟联网检索
    # ------------------------------------------------------------------
    def simulated_network_search(self, course: str, preferences: List[str]) -> List[Dict[str, str]]:
        """
        模拟联网检索，生成动态补充资源
        预留替换为真实API的接口（使用函数指针或接口类替换此方法即可）

        Args:
            course: 课程名称
            preferences: 学习偏好列表
        Returns:
            模拟联网资源列表
        """
        results = []

        # 偏好 → 模拟搜索结果映射
        pref_search_map = {
            "视频": [
                {"title": f"B站热门教程「{course}」2026年最新版", "source": "B站(联网)", "url": f"https://search.bilibili.com/all?keyword={course}+2026",
                 "desc": f"2026年最新上传的{course}教程，播放量已破百万，弹幕互动活跃"},
                {"title": f"YouTube「{course} Full Course」热门系列", "source": "YouTube(联网)", "url": f"https://www.youtube.com/results?search_query={course}+full+course",
                 "desc": "英文授课，自动翻译中文字幕，国际社区评价极高"},
            ],
            "实操": [
                {"title": f"GitHub Trending「{course}」实战项目", "source": "GitHub(联网)", "url": f"https://github.com/trending?since=monthly&spoken_language_code=zh",
                 "desc": f"本月GitHub Trending上{course}相关热门开源项目，含中文README"},
                {"title": f"知乎「{course}」实战经验高赞回答汇总", "source": "知乎(联网)", "url": f"https://www.zhihu.com/search?type=content&q={course}+实战",
                 "desc": f"知乎高赞回答中整理的{course}实操路线图和踩坑记录"},
            ],
            "刷题": [
                {"title": f"LeetCode「{course}」最新高频题合集 2026", "source": "LeetCode(联网)", "url": f"https://leetcode.cn/problemset/all/",
                 "desc": f"近6个月大厂面试中{course}相关高频题目，含社区最优解"},
                {"title": f"牛客网「{course}」专项练习最新题库", "source": "牛客网(联网)", "url": f"https://www.nowcoder.com/exam/oj",
                 "desc": "最新更新的题库，支持在线判题和错题本功能"},
            ],
            "文档": [
                {"title": f"GitHub Awesome「{course}」资源合集 2026", "source": "GitHub(联网)", "url": f"https://github.com/search?q=awesome+{course}",
                 "desc": f"社区维护的{course}学习资源精选列表，持续更新中"},
                {"title": f"CSDN/掘金「{course}」2026热门技术文章", "source": "CSDN/掘金(联网)", "url": f"https://so.csdn.net/so/search?q={course}",
                 "desc": f"2026年{course}领域最受欢迎的技术博客和学习笔记"},
            ],
        }

        added_sources = set()
        if preferences:
            for pref in preferences:
                if pref in pref_search_map:
                    for item in pref_search_map[pref]:
                        if item["source"] not in added_sources:
                            added_sources.add(item["source"])
                            results.append(item)
        else:
            # 每种偏好各取1个
            for pref_type in ["文档", "视频"]:
                if pref_type in pref_search_map:
                    results.append(pref_search_map[pref_type][0])

        return results[:4]  # 最多4个联网资源

    # ------------------------------------------------------------------
    # 方法4: 合并资源
    # ------------------------------------------------------------------
    def merge_resources(
        self, local: List[Dict[str, str]], network: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        合并本地+模拟联网资源，自动去重
        Args:
            local: 本地资源列表
            network: 联网资源列表
        Returns:
            (local_deduped, network_deduped)
        """
        # 用标题相似度去重（简单：检查本地标题关键词是否在联网结果中）
        local_titles = {r["title"] for r in local}
        network_deduped = []
        for n in network:
            is_dup = False
            for lt in local_titles:
                # 简单判重：如果联网标题包含本地标题的核心关键词
                lt_core = re.sub(r'[《》「」""]', '', lt)[:10]
                if len(lt_core) >= 4 and lt_core in n["title"]:
                    is_dup = True
                    break
            if not is_dup:
                network_deduped.append(n)

        return local, network_deduped

    # ------------------------------------------------------------------
    # 方法5: 生成最终推荐报告
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        """
        生成最终的【学习画像 + 推荐资源】报告
        Returns:
            Markdown 格式的报告
        """
        course = self.extracted.get("course") or self.course_name or "未知"
        basis = self.extracted.get("basis") or "待确认"
        prefs = self.extracted.get("preferences") or ["文档", "视频"]
        pace = self.extracted.get("pace") or "正常"

        # 查询两层资源
        local = self.local_resource_query(course, prefs)
        network = self.simulated_network_search(course, prefs)
        local, network = self.merge_resources(local, network)

        # 构建报告
        report = ""

        # --- 学习画像 ---
        report += "## 📋 学习画像\n\n"
        report += f"| 维度 | 内容 |\n"
        report += f"|------|------|\n"
        report += f"| 课程 | **{course}** |\n"
        report += f"| 基础 | {basis} |\n"
        report += f"| 学习偏好 | {', '.join(prefs)} |\n"
        report += f"| 学习节奏 | {pace} |\n"
        if self.extracted.get("goals") and self.extracted["goals"] != "待了解":
            report += f"| 学习目标 | {self.extracted['goals']} |\n"
        if self.extracted.get("weakness") and self.extracted["weakness"] != "待了解":
            report += f"| 薄弱环节 | {self.extracted['weakness']} |\n"
        report += "\n"

        # --- 本地基础资源 ---
        report += "## 📚 推荐学习资源\n\n"
        report += "### === 本地基础资源（兜底） ===\n\n"
        if local:
            for i, r in enumerate(local, 1):
                url_part = f" → [链接]({r['url']})" if r.get("url") else ""
                report += f"{i}. **{r['title']}**\n"
                report += f"   📍 来源：{r['source']}{url_part}\n"
                report += f"   📝 {r['desc']}\n\n"
        else:
            report += "暂无匹配的本地资源，请尝试更换课程或偏好。\n\n"

        # --- 动态补充资源 ---
        report += "### === 动态补充资源（联网检索） ===\n\n"
        report += "> ⚡ 以下为模拟联网检索结果，标记「联网」的资源来自外部平台。\n"
        report += "> 后期可将 `simulated_network_search()` 方法替换为真实 API 调用。\n\n"
        if network:
            for i, r in enumerate(network, 1):
                url_part = f" → [链接]({r['url']})" if r.get("url") else ""
                report += f"{i}. **{r['title']}**\n"
                report += f"   📍 来源：{r['source']}{url_part}\n"
                report += f"   📝 {r['desc']}\n\n"
        else:
            report += "暂无新的联网补充资源。\n\n"

        # --- 学习建议 ---
        report += "---\n\n"
        report += "## 💡 学习建议\n\n"
        if "实操" in prefs and basis in ("零基础", "入门"):
            report += "- 建议先通过基础视频/文档快速了解核心概念，再进入实操阶段，避免一开始就遇到太多障碍。\n"
        if "视频" in prefs and pace == "精读":
            report += "- 视频学习时可以适当做笔记，遇到代码片段暂停跟着敲一遍，加深理解。\n"
        if "刷题" in prefs:
            report += "- 刷题时建议按主题分类练习，先理解核心思路再看答案，形成自己的解题思维。\n"
        report += f"- 学习节奏「{pace}」：{'快速过一遍即可，重点抓核心概念，遇到卡点再深究。' if pace == '快速' else '按正常进度推进，每学完一个章节做一次回顾。' if pace == '正常' else '不追求速度，确保每个知识点彻底理解再前进，多问自己为什么。'}\n"

        return report

    # ------------------------------------------------------------------
    # 方法6: 处理单轮对话输入（供 Streamlit 调用）
    # ------------------------------------------------------------------
    def process_input(self, user_input: str) -> Dict[str, any]:
        """
        处理用户的单轮输入，更新提取信息并返回下一问
        Args:
            user_input: 用户当前回答
        Returns:
            {
                "extracted": {...},       # 本轮提取的关键词
                "next_question": str,     # 下一个问题（空字符串表示对话完成）
                "is_complete": bool,      # 对话是否完成
                "report": str,            # 完成后生成的报告
            }
        """
        # 记录历史
        self.dialogue_history.append({"role": "user", "content": user_input})

        # 提取关键词
        keywords = self.extract_keywords(user_input)

        # 更新 accumulated 信息
        if keywords.get("course") and not self.extracted["course"]:
            self.extracted["course"] = keywords["course"]
        if keywords.get("basis") and not self.extracted["basis"]:
            self.extracted["basis"] = keywords["basis"]
        for p in keywords.get("preferences", []):
            if p not in self.extracted["preferences"]:
                self.extracted["preferences"].append(p)
        if keywords.get("pace") and not self.extracted["pace"]:
            self.extracted["pace"] = keywords["pace"]

        # 推进对话轮次
        self.dialogue_round += 1
        next_q = ""
        is_complete = False
        report = ""

        if self.dialogue_round < len(self.questions):
            next_q = self.questions[self.dialogue_round]
        else:
            # 所有问题问完
            is_complete = True
            # 如果没有任何偏好，默认给一个
            if not self.extracted["preferences"]:
                self.extracted["preferences"] = ["文档", "视频"]
            if not self.extracted["pace"]:
                self.extracted["pace"] = "正常"
            report = self.generate_report()

        return {
            "extracted": keywords,
            "next_question": next_q,
            "is_complete": is_complete,
            "report": report,
        }

    def get_first_question(self) -> str:
        """获取对话的第一个问题"""
        if self.questions:
            return self.questions[0]
        return "请告诉我你想学习哪门课程？"

    def get_questions_count(self) -> int:
        """获取总问题数"""
        return len(self.questions)


# ============================================================================
# 便捷函数
# ============================================================================
def create_dialogue_agent(course_name: str = "", profile: dict = None) -> DialogueResourceAgent:
    """创建对话资源智能体实例"""
    return DialogueResourceAgent(course_name=course_name, profile=profile)


def generate_knowledge_map(course_name: str, profile: dict = None) -> str:
    """生成第5类资源: 知识结构图（调用 LLM）

    Args:
        course_name: 课程名称
        profile: 学生画像 dict (中文 key)

    Returns:
        知识结构图 Markdown，失败返回空字符串
    """
    try:
        from agents import create_agents, run_with_fallback
        import json as _json

        agents_factory = create_agents(course_name=course_name)
        km_agent = agents_factory.resource_agent()

        profile_str = _json.dumps(profile or {}, ensure_ascii=False)
        prompt = f"""请为课程"{course_name}"生成一份知识结构图（知识体系树状图）。

要求:
- 用 ASCII 树状图/大纲展示课程的核心知识体系
- 标注各模块的层级关系（基础→进阶→高级）
- 标注重点(★)和难点(▲)
- 根据学生薄弱环节，在对应节点标注"需加强"

学生画像: {profile_str}

只输出知识结构图，不要其他内容。"""
        resp, _ = run_with_fallback(km_agent, prompt)
        if resp and len(resp) > 20:
            return "\n\n---\n\n## 🟠 知识结构图（第5类资源）\n\n" + resp
    except Exception:
        pass
    return ""


# ============================================================================
# 独立运行演示
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  DialogueResourceAgent 独立演示")
    print("  对话式学习偏好提取 + 本地库兜底 + 模拟联网补充")
    print("=" * 60)
    print()

    agent = DialogueResourceAgent(course_name="C语言")
    print(f"🤖 AI: {agent.get_first_question()}")
    print()

    while True:
        user_input = input("👤 你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "退出"):
            print("👋 再见！")
            break

        result = agent.process_input(user_input)

        if result["is_complete"]:
            print()
            print("🤖 AI: 好的，我已经了解你的学习偏好了！以下是为你的个性化推荐：")
            print()
            print(result["report"])
            break
        else:
            print(f"🤖 AI: {result['next_question']}")
            print()
