import uuid
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import tools_condition
from langchain_core.runnables import RunnableConfig 

from graph_chat.assistant import CtripAssistant, assistant_runnable, primary_assistant_tools
from graph_chat.base_data_model import ToFlightBookingAssistant, ToBookCarRental, ToHotelBookingAssistant, ToBookExcursion
from graph_chat.build_child_graph import build_flight_graph, builder_hotel_graph, build_car_graph, builder_excursion_graph
from tools.flights_tools import fetch_user_flight_information
from graph_chat.draw_png import draw_graph
from graph_chat.state import State
from tools.init_db import update_dates
from tools.tools_handler import create_tool_node_with_fallback, _print_event

# ==========================================
# 1. 定义流程图的构建对象
# ==========================================
builder = StateGraph(State)

def get_user_info(state: State, config: RunnableConfig):
    # 注入用户航班上下文，必须带上 config 以获取 passenger_id
    return {"user_info": fetch_user_flight_information.invoke({}, config)}

# 2. fetch_user_info节点首先运行，作为全局数据初始化的第一站
builder.add_node('fetch_user_info', get_user_info)
builder.add_edge(START, 'fetch_user_info')

# ==========================================
# 3. 注册四个业务助理的子工作流
# ==========================================
builder = build_flight_graph(builder)
builder = builder_hotel_graph(builder)
builder = build_car_graph(builder)
builder = builder_excursion_graph(builder)

# ==========================================
# 4. 添加主助理节点及其工具节点
# ==========================================
builder.add_node('primary_assistant', CtripAssistant(assistant_runnable))

# 🌟 这里的 primary_assistant_tools 在 assistant.py 中已经包含了 web_search 和 fetch_user_flight_information
builder.add_node(
    "primary_assistant_tools", create_tool_node_with_fallback(primary_assistant_tools)
)

def route_primary_assistant(state: dict):
    """根据当前状态判断路由到子助手节点还是执行安全工具。"""
    route = tools_condition(state)
    if route == END:
        return END
        
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        # 如果是业务分发指令，路由到对应的子助理
        if tool_calls[0]["name"] == ToFlightBookingAssistant.__name__:
            return "enter_update_flight"
        elif tool_calls[0]["name"] == ToBookCarRental.__name__:
            return "enter_book_car_rental"
        elif tool_calls[0]["name"] == ToHotelBookingAssistant.__name__:
            return "enter_book_hotel"
        elif tool_calls[0]["name"] == ToBookExcursion.__name__:
            return "enter_book_excursion"
            
        # 🌟 核心兼容点：如果调用的不是上面的路由工具（比如 web_search），
        # 则默认流转到主助理的安全工具节点直接执行，不触发拦截！
        return "primary_assistant_tools"
        
    raise ValueError("无效的路由")

# 绑定主助理的条件路由边
builder.add_conditional_edges(
    'primary_assistant',
    route_primary_assistant,
    [
        "enter_update_flight",
        "enter_book_car_rental",
        "enter_book_hotel",
        "enter_book_excursion",
        "primary_assistant_tools",
        END,
    ]
)

# 工具执行完毕后，必须无条件返回给主助理继续思考
builder.add_edge('primary_assistant_tools', 'primary_assistant')

def route_to_workflow(state: dict) -> str:
    """断点恢复路由：如果我们在一个委托的状态中，直接路由到相应的激活助理。"""
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "primary_assistant"
    return dialog_state[-1]

# 连接起始数据获取节点到动态路由
builder.add_conditional_edges("fetch_user_info", route_to_workflow)

# ==========================================
# 5. 编译状态图，配置检查点和敏感操作中断点 (HITL)
# ==========================================
memory = MemorySaver()
graph = builder.compile(
    checkpointer=memory,
    # 这里只拦截修改数据库的敏感操作，主助理的 web_search 不在此列，所以能畅通无阻全自动运行
    interrupt_before=[
        "update_flight_sensitive_tools",
        "book_car_rental_sensitive_tools",
        "book_hotel_sensitive_tools",
        "book_excursion_sensitive_tools",
    ]
)