# 携程多智能体旅行助手 LangGraph-Booking-Agent
> 基于 **LangGraph** 和 **Streamlit** 构建的生产级智能旅行大管家。

系统不仅能处理复杂的自然语言查询，还能通过多个专业 Agent（机票、酒店、租车、游览）的协同工作来完成真实业务，并具备关键动作的**安全拦截与人工审批**功能。

---
## 界面展示

### 租车服务与人工介入审批
<img width="1860" height="1956" alt="41f17b699dadd2b9786f59ee896a404c" src="https://github.com/user-attachments/assets/fe47182a-176b-42f0-89f5-c5de283c7d2d" />

### 酒店订购服务
<img width="1860" height="1930" alt="4cadccfddd6e32f1d4dc51d63d30952f" src="https://github.com/user-attachments/assets/f29629b3-0da8-4d26-952e-68b28985a20d" />

### 航班订购服务
<img width="1860" height="1561" alt="60ea058603195e48706a7ef8dc025596" src="https://github.com/user-attachments/assets/bb1ff661-3a78-47af-a4d6-bd8e3918cd18" />

---
## 核心特性

- **多智能体协同架构 (Multi-Agent Architecture)**：采用“主助理 + 专家助理”模式。主助理负责意图分发，子助理负责垂直领域（机票/酒店/租车/游览）的深度交互。
- **人工介入审批 (Human-in-the-loop)**：针对改签、退票、下单等敏感操作，系统会自动进入中断状态并弹出 UI 审批卡片，用户授权后方可修改数据库。
- **状态机持久化 (State Persistence)**：集成 `MemorySaver` 检查点，支持对话中断恢复和多轮上下文记忆。
- **实时数据库查看器 (DB Viewer)**：在 Web 页面顶部内置折叠面板，可实时通过交互式表格查看 SQLite 后台数据变动。
- **极高的稳定性 (Robustness)**：
    - **逻辑熔断**：在 `assistant.py` 中内置 `max_retries` 机制，防止 AI 陷入工具调用死循环。
    - **路径兼容**：采用动态绝对路径加载数据库，彻底解决多层文件夹下的路径错位问题。
    - **流转限制**：配置 `recursion_limit` 为 100 步，支持复杂的跨领域业务流转。

---

## 项目结构

```text
trip_assistant/
├── app.py                  # Streamlit Web 前端界面与交互逻辑
├── travel_new.sqlite       # SQLite 业务数据库 (存储机票、酒店、租车等数据)
├── graph_chat/             # 后端核心逻辑包
│   ├── 第三个流程图.py       # LangGraph 状态图定义与编译中心
│   ├── assistant.py        # 智能体类定义 (含死循环保护机制)
│   ├── agent_assistant.py  # 各领域 Agent 的 Prompt 提示词与逻辑
│   ├── state.py            # 定义全局状态 (State) 结构
│   ├── build_child_graph.py # 子助理工作流构建
│   └── ...
├── tools/                  # 业务工具库 (SQL 操作层)
│   ├── car_tools.py        # 租车业务工具集
│   ├── flights_tools.py    # 机票业务工具集
│   ├── init_db.py          # 数据库初始化与日期同步工具
│   └── tools_handler.py    # 工具调用错误处理拦截器
└── requirements.txt        # 项目依赖
```
---
## 快速开始
### 1. 克隆项目并安装依赖
建议使用 Python 3.9 或更高版本：

```Bash
# 进入项目目录
cd trip_assistant

# 安装必要依赖
pip install streamlit langchain langchain-openai langgraph pandas openpyxl
```

### 2. 配置 API Key
确保您的环境变量中已配置大模型 API 密钥（如 OpenAI 或 ZhipuAI）：

```Bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 启动应用
在 trip_assistant 根目录下运行：

```Bash
streamlit run app.py
```

## 后续规划
- 接入微信，实现消息通知与提醒（较易）
- 跳出本地数据库限制，实现携程软件api接口调用与订票服务（较难）
