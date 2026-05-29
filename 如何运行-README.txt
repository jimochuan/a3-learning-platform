================================================================
  A3 v3 个性化学习多智能体系统 — 运行指南
  六智能体协作 · DeepSeek 主力模型 · 讯飞星火交叉验证
================================================================

环境要求
--------
  - Python >= 3.10（建议 3.11 或 3.12）
  - Windows / macOS / Linux 均可
  - 需要能访问外网（调用 DeepSeek / 星火 API）


快速启动（3 步）
---------------

  1. 双击「启动Web界面.bat」

     首次运行会自动引导你粘贴 API Key，之后再次启动不会再问。


  2. 粘贴你的 DeepSeek API Key

     脚本会提示你粘贴 Key。先去 https://platform.deepseek.com 注册，
     注册后点左侧「API Keys」→「创建新 Key」→ 复制 sk- 开头的那串，
     回到窗口粘贴，回车即可。

     如果暂时没有 Key，直接按回车跳过，系统会用内置星火兜底也能跑。


  3. 浏览器自动打开 http://localhost:8501，注册账号开始使用


命令行启动（macOS / Linux / 不用 bat 时）
-----------------------------------------

  1. 安装依赖

      pip install -r requirements.txt

     下载慢换国内镜像：

      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


  2. 配置 API Key

     首次运行会自动检测并提示你粘贴 Key，无需手动编辑文件。
     如果手动配：复制 .env.example 为 .env，编辑 DEEPSEEK_API_KEY 那一行。

     | 模型         | 推荐度    | 注册地址                            | 费用说明               |
     |--------------|-----------|-------------------------------------|-----------------------|
     | DeepSeek     | ☆☆☆ 首选  | https://platform.deepseek.com       | 注册送额度，充值 10 元够用很久 |
     | 讯飞星火     | ☆☆ 备用   | https://console.xfyun.cn            | 免费领取 Lite 额度     |
     | 智谱 GLM     | ☆ 可选    | https://open.bigmodel.cn            | 有免费额度             |


  3. 启动

      streamlit run app.py

     或者：

      python main.py


功能流程
--------

  登录后经过 5 个步骤：

  1. AI 对话画像   — 跟 AI 聊你想学什么，自动提取学习画像
  2. 资源推荐     — 根据画像推荐视频、实操、刷题、文档
  3. 学习路径     — 生成 5 步个性化学习路线
  4. 智能辅导     — 随时提问，AI 导师解答
  5. 学习评估     — 双模型交叉验证评估报告


项目结构
--------

  a3_v3/
  ├── app.py                      # 主界面（Streamlit）
  ├── main.py                     # 入口脚本
  ├── config.py                   # 配置（自动读取 .env）
  ├── agents.py                   # AI Agent 工厂
  ├── dialogue_resource_agent.py  # 资源推荐对话引擎
  ├── rag_helper.py               # RAG 知识库检索
  ├── auth.py                     # 用户认证逻辑
  ├── auth_pages.py               # 登录/注册/忘记密码页面
  ├── user_store.py               # 用户数据存储
  ├── login_state.py              # 登录状态管理
  ├── requirements.txt            # Python 依赖
  ├── .env.example                # 环境变量模板
  ├── .gitignore                  # Git 排除规则
  ├── knowledge/                  # 课程知识库（JSON）
  ├── modules/                    # 五步学习流程模块
  ├── providers/                  # 多模型供应商适配
  ├── shared/                     # 共享组件层
  └── docs/                       # 文档


常见问题
--------

  Q: 启动报错 ModuleNotFoundError: No module named 'xxx'
  A: 依赖没装全，再跑一次 pip install -r requirements.txt

  Q: 聊天一直显示「星火(备用)」而不是 DeepSeek
  A: 说明 DeepSeek Key 没生效。删掉 .env 文件重新双击 bat 粘贴 Key，
     或手动检查 .env 里的 DEEPSEEK_API_KEY 是否正确。

  Q: Streamlit 端口被占用
  A: 指定其他端口：streamlit run app.py --server.port 8502

  Q: 想改课程内容
  A: 编辑 knowledge/ 目录下的 JSON 文件，或修改 config.py 的 COURSES 字典。

  Q: 用户数据存在哪
  A: user_data/ 目录（运行时自动创建），JSON 文件存储，每人一个文件。

  Q: 想换 Key 或重新配置
  A: 删掉项目里的 .env 文件，重新双击 bat 即可重新配置。
