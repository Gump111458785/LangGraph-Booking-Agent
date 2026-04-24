import streamlit as st
import uuid
from langchain_core.messages import ToolMessage

# 精确导入你的 graph 对象和初始化数据库的函数
# 把原来带 trip_assistant 前缀的两行，改成下面这样：
from graph_chat.第三个流程图 import graph
from tools.init_db import update_dates

# ==========================================
# 1. 页面基本配置与全局状态初始化
# ==========================================
st.set_page_config(page_title="携程多Agent旅行助手", page_icon="✈️", layout="wide")
st.title("✈️ 携程智能旅行大管家")
st.caption("基于 LangGraph 构建的多智能体协同工作流（支持 Human-in-the-loop 人类介入审批）")

# 初始化会话 Session ID (用来追踪内存检查点 memory)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    # 每次开启全新会话时，重置数据库的测试时间
    update_dates()

# 初始化测试用的固定乘客 ID (对应数据库里有数据的旅客)
if "passenger_id" not in st.session_state:
    st.session_state.passenger_id = "3442 587242"

# 初始化前端显示的聊天历史记录数组
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 初始化控制前端页面状态的标志：是否处于等待人类审批中断的状态
if "awaiting_approval" not in st.session_state:
    st.session_state.awaiting_approval = False

# 封装传递给 LangGraph 的线程配置字典
config = {
    "configurable": {
        "passenger_id": st.session_state.passenger_id,
        "thread_id": st.session_state.session_id,
    },
    "recursion_limit": 100
}

# ==========================================
# 2. 侧边栏 UI 配置
# ==========================================
with st.sidebar:
    st.header("⚙️ 调试面板")
    st.text_input("乘客 ID (Passenger ID)", value=st.session_state.passenger_id, disabled=True)
    st.text_input("会话 ID (Thread ID)", value=st.session_state.session_id, disabled=True)
    
    # 清空上下文并重启后端的重置按钮
    if st.button("🔄 重置会话与数据库", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.awaiting_approval = False
        update_dates()
        st.rerun()  # 立即刷新页面
# ==========================================
# 2.5 🗄️ 实时数据库查看视图 (新增功能)
# ==========================================
with st.expander("🗄️ 点击此处：实时查看后台数据库内容 (DB Viewer)", expanded=False):
    import sqlite3
    import pandas as pd
    import os
    
    # 智能识别数据库路径 (兼容不同的运行目录)
    db_path = "../travel_new.sqlite" if os.path.exists("../travel_new.sqlite") else "travel_new.sqlite"
    
    try:
        # 连接本地 SQLite 数据库
        conn = sqlite3.connect(db_path)
        
        # 查询数据库中所有的表名
        tables_df = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        table_names = tables_df['name'].tolist()
        
        if table_names:
            # 渲染一个下拉菜单，让用户选择看哪张表
            selected_table = st.selectbox("请选择你要查看的业务表：", table_names, key="db_table_select")
            
            # 读取用户选中的那张表的全部数据
            df = pd.read_sql(f"SELECT * FROM {selected_table}", conn)
            
            # 渲染出漂亮的交互式表格
            st.dataframe(
                df, 
                use_container_width=True, # 宽度自动撑满
                hide_index=True           # 隐藏最左边难看的数字索引
            )
        else:
            st.warning("数据库是空的，没有找到任何表。")
            
        conn.close()
    except Exception as e:
        st.error(f"读取数据库失败，可能是路径问题，请检查。详细报错: {e}")

# ==========================================
# 3. 渲染历史聊天记录
# ==========================================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. 核心拦截逻辑：捕捉 Graph 的中断状态 (审批卡片)
# ==========================================
current_state = graph.get_state(config)

if current_state.next:
    st.session_state.awaiting_approval = True
    st.warning("⚠️ **系统拦截：检测到敏感修改操作（如退票、改签、下单），必须获得您的授权方可执行！**")
    
    # 🌟 修复点：防御性查找！倒序遍历消息栈，找到最近的一条带有 tool_calls 的消息
    messages = current_state.values.get("messages", [])
    last_ai_message = next((msg for msg in reversed(messages) if hasattr(msg, 'tool_calls') and msg.tool_calls), None)
    
    # 如果成功找到了工具调用请求
    if last_ai_message:
        tool_call = last_ai_message.tool_calls[0]
        st.info(f"**🤖 AI 申请执行工具**: `{tool_call['name']}`\n\n**📝 提取到的参数**: `{tool_call['args']}`")
        
        col1, col2 = st.columns(2)
        
        # 左侧按钮：同意
        with col1:
            if st.button("✅ 批准执行", use_container_width=True):
                with st.spinner("系统正在处理业务，请稍候..."):
                    try:
                        events = graph.stream(None, config, stream_mode='values')
                        final_event = None
                        
                        # 使用安全的 for 循环替代容易崩溃的 list()[-1]
                        for event in events:
                            final_event = event
                            # 打印后台轨迹，方便抓虫
                            print("👉 [批准后-流转节点]:", event.get("dialog_state", ["primary_assistant"])[-1])
                            
                        # 安全提取最终回复
                        if final_event and "messages" in final_event and len(final_event["messages"]) > 0:
                            ai_reply = final_event["messages"][-1].content
                            if ai_reply:
                                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                    except Exception as e:
                        st.error("执行业务时发生异常！请查看终端日志。")
                        print("❌ 批准执行报错:", e)
                        
                st.session_state.awaiting_approval = False
                st.rerun()
                
        # 右侧按钮：拒绝
        with col2:
            reject_reason = st.text_input("如拒绝，请填写修改要求（选填）：", key="reject_input")
            if st.button("❌ 驳回并修改", use_container_width=True):
                reason = reject_reason if reject_reason.strip() else "用户手动驳回了该工具操作"
                with st.spinner("正在将驳回意见反馈给 AI 重新评估..."):
                    try:
                        result = graph.stream(
                            {
                                "messages": [
                                    ToolMessage(
                                        tool_call_id=tool_call["id"],
                                        content=f"Tool的调用被用户拒绝。原因：'{reason}'。",
                                    )
                                ]
                            },
                            config,
                        )
                        final_event = None
                        for event in result:
                            final_event = event
                            print("👉 [驳回后-流转节点]:", event.get("dialog_state", ["primary_assistant"])[-1])
                            
                        if final_event and "messages" in final_event and len(final_event["messages"]) > 0:
                            ai_reply = final_event["messages"][-1].content
                            if ai_reply:
                                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                    except Exception as e:
                        st.error("处理驳回逻辑时发生异常！")
                        print("❌ 驳回操作报错:", e)
                        
                st.session_state.awaiting_approval = False
                st.rerun()

# ==========================================
# 5. 常规对话输入框
# ==========================================
# 只有在系统没有被中断拦截（没有显示审批卡片）时，才允许用户发起新的对话
if not st.session_state.awaiting_approval:
    user_input = st.chat_input("您好！请问有什么我可以帮您的（查航班/退改签/订酒店）？")
    
    if user_input:
        # 1. 立即上屏展示用户的提问
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2. 调用底层大模型进行处理
        with st.chat_message("assistant"):
            with st.spinner("🧠 携程 AI 思考中，正在调度专家网络..."):
                try:
                    # 使用列表形式传入 user_input，防止某些版本的类型严格校验
                    events = graph.stream({'messages': [('user', user_input)]}, config, stream_mode='values')
                    
                    final_event = None
                    # 将每一次中间状态打印到终端控制台，方便抓虫
                    for event in events:
                        final_event = event
                        
                        current_dialog_state = event.get("dialog_state", ["primary_assistant"])
                        if current_dialog_state:
                            print("👉 [流转节点]:", current_dialog_state[-1])
                            
                        msgs = event.get("messages", [])
                        if msgs:
                            msg = msgs[-1]
                            if hasattr(msg, 'content') and msg.content:
                                print("   [文本输出]:", msg.content)
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                print("   [调用工具]:", msg.tool_calls[0]['name'])

                    # 循环结束后，安全地提取最终消息 (加入严格的防御性判断)
                    if final_event and "messages" in final_event and len(final_event["messages"]) > 0:
                        latest_message = final_event["messages"][-1]
                        
                        # 情况 A：模型给出了纯文本的回复解答
                        if hasattr(latest_message, 'content') and latest_message.content:
                            ai_reply = latest_message.content
                            st.markdown(ai_reply)
                            st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                            
                        # 情况 B：模型决定发起工具调用修改数据
                        if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                            st.write(f"⚙️ 正在启动业务组件 `{latest_message.tool_calls[0]['name']}`，即将申请授权...")
                    else:
                        st.warning("⚠️ 模型执行完毕，但没有返回任何有效消息。")

                except Exception as e:
                    st.error(f"系统运行出错，已记录日志。")
                    print("\n❌ ============ 严重报错详情 ============")
                    print(e)
                    print("=======================================\n")
                    
        # 无论成功或失败，最后刷新页面状态
        st.rerun()