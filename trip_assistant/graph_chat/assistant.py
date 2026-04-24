import os
from datetime import datetime

from langchain_community.tools import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_openai import ChatOpenAI

from graph_chat.base_data_model import ToFlightBookingAssistant, ToBookCarRental, ToHotelBookingAssistant, \
    ToBookExcursion
from graph_chat.llm_tavily import tavily_tool, llm
from graph_chat.state import State
from tools.car_tools import search_car_rentals, book_car_rental, update_car_rental, cancel_car_rental
from tools.flights_tools import fetch_user_flight_information, search_flights, update_ticket_to_new_flight, \
    cancel_ticket
from tools.hotels_tools import search_hotels, book_hotel, update_hotel, cancel_hotel
from tools.retriever_vector import lookup_policy
from tools.trip_tools import search_trip_recommendations, book_excursion, update_excursion, cancel_excursion
from langchain_core.runnables import RunnableSerializable, RunnableConfig
# 确保文件里也有这个导入，如果没有请加上：
from datetime import datetime
from tools.web_tools import web_search

class CtripAssistant:
    def __init__(self, runnable: RunnableSerializable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        # 🌟 修改点：只允许重试 3 次，防止死循环把 API 刷爆
        max_retries = 3
        while max_retries > 0:
            result = self.runnable.invoke(state, config)
            
            # 如果 AI 既没说话也没调工具，通常是模型幻觉或报错了
            if not result.tool_calls and (
                not result.content
                or (isinstance(result.content, list) and not result.content[0].get("text"))
            ):
                messages = state["messages"] + [("user", "请提供一个真实的输出作为回应。")]
                state = {**state, "messages": messages}
                max_retries -= 1  # 消耗一次机会
            else:
                break
        
        if max_retries == 0:
            # 如果试了3次都不行，强行返回一个提示，避免系统崩溃
            return {"messages": [("assistant", "抱歉，系统处理出现异常，请稍后再试。")]}
            
        return {"messages": result}



# 主助理提示模板
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是携程瑞士航空公司的客户服务助理。"
            "如果用户询问天气、旅游攻略、新闻等外部实时信息，请直接调用 web_search 工具解答。"
            "您的主要职责是搜索航班信息和公司政策以回答客户的查询。"
            "如果客户请求更新或取消航班、预订租车、预订酒店或获取旅行推荐，请通过调用相应的工具将任务委派给合适的专门助理。您自己无法进行这些类型的更改。"
            "只有专门助理才有权限为用户执行这些操作。"
            "用户并不知道有不同的专门助理存在，因此请不要提及他们；只需通过函数调用来安静地委派任务。"
            "向客户提供详细的信息，并且在确定信息不可用之前总是复查数据库。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "如果搜索无果，请扩大搜索范围后再放弃。"
            "\n\n当前用户的航班信息:\n<Flights>\n{user_info}\n</Flights>"
            "\n当前时间: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

# 定义主助理使用的工具
primary_assistant_tools = [
    tavily_tool,  # 假设TavilySearchResults是一个有效的搜索工具
    search_flights,  # 搜索航班的工具
    lookup_policy,  # 查找公司政策的工具
    web_search,
]

# 创建可运行对象，绑定主助理提示模板和工具集，包括委派给专门助理的工具
assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools
    + [
        ToFlightBookingAssistant,  # 用于转交航班更新或取消的任务
        ToBookCarRental,  # 用于转交租车预订的任务
        ToHotelBookingAssistant,  # 用于转交酒店预订的任务
        ToBookExcursion,  # 用于转交旅行推荐和其他游览预订的任务
    ]
)

