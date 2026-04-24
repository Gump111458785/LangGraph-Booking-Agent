from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from graph_chat.base_data_model import CompleteOrEscalate
from graph_chat.llm_tavily import llm
from tools.car_tools import search_car_rentals, book_car_rental, update_car_rental, cancel_car_rental
from tools.flights_tools import search_flights, update_ticket_to_new_flight, cancel_ticket
from tools.hotels_tools import search_hotels, book_hotel, update_hotel, cancel_hotel
from tools.trip_tools import search_trip_recommendations, book_excursion, update_excursion, cancel_excursion
from tools.web_tools import web_search
# 航班预订助手
flight_booking_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是专门处理航班查询，改签和预定的助理。"
            "用户的当前航班信息已经提供在下面 <Flights> 标签中，**请直接阅读，绝对不要尝试调用工具去查询用户的当前机票**。"
            "\n\n🚨 【重要改签流程规范】 🚨\n"
            "当用户要求改签航班时，你必须严格按照以下两步执行：\n"
            "第一步：使用 `search_flights` 工具，搜索用户想要改签到的目标日期和航班号，以获取目标航班真实的 `flight_id`。\n"
            "第二步：使用 `update_ticket_to_new_flight` 工具，传入用户原有的 `ticket_no` 和你刚查到的 `new_flight_id`，完成改签操作。"
            "\n\n当前用户的航班信息:\n<Flights>\n{user_info}\n</Flights>"
            "\n当前时间: {time}."
            "\n\n如果用户需要帮助，并且您的工具都不适用，则"
            '“CompleteOrEscalate”对话给主助理。不要浪费用户的时间。',
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

# 定义安全工具（只读操作）和敏感工具（涉及更改的操作）
update_flight_safe_tools = [search_flights]
update_flight_sensitive_tools = [update_ticket_to_new_flight, cancel_ticket]

# 合并所有工具
update_flight_tools = update_flight_safe_tools + update_flight_sensitive_tools

# 创建可运行对象，绑定航班预订提示模板和工具集，包括CompleteOrEscalate工具
update_flight_runnable = flight_booking_prompt | llm.bind_tools(
    update_flight_tools + [CompleteOrEscalate]
)

# 酒店预订助手
book_hotel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是专门处理酒店预订的助理。"
            "当用户需要帮助预订酒店时，主助理会将工作委托给您。"
            "根据用户的偏好搜索可用酒店，并与客户确认预订详情。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "如果您需要更多信息或客户改变主意，请将任务升级回主助理。"
            "请记住，在相关工具成功使用后，预订才算完成。"
            "\n当前时间: {time}."
            "\n\n如果用户需要帮助，并且您的工具都不适用，则"
            '“CompleteOrEscalate”对话给主助理。不要浪费用户的时间。不要编造无效的工具或功能。'
            "\n\n以下是一些你应该CompleteOrEscalate的例子：\n"
            " - '这个季节的天气怎么样？'\n"
            " - '我再考虑一下，可能单独预订'\n"
            " - '我需要弄清楚我在那里的交通方式'\n"
            " - '哦，等等，我还没预订航班，我会先订航班'\n"
            " - '酒店预订已确认'",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

# 定义安全工具（只读操作）和敏感工具（涉及更改的操作）
book_hotel_safe_tools = [search_hotels]
book_hotel_sensitive_tools = [book_hotel, update_hotel, cancel_hotel]

# 合并所有工具
book_hotel_tools = book_hotel_safe_tools + book_hotel_sensitive_tools

# 创建可运行对象，绑定酒店预订提示模板和工具集，包括CompleteOrEscalate工具
book_hotel_runnable = book_hotel_prompt | llm.bind_tools(
    book_hotel_tools + [CompleteOrEscalate]
)

# 租车预订助手
book_car_rental_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是专门处理租车预订的助理。"
            "当用户需要帮助预订租车时，主助理会将工作委托给您。"
            "根据用户的偏好搜索可用租车，并与客户确认预订详情。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "请记住，在相关工具成功使用后，预订才算完成。"
            "\n当前时间: {time}."
            "\n\n🚨 【重要跨域处理规则】 🚨\n"
            "如果你收到任何不属于你业务范围内的请求（例如：查询或预订机票、酒店、退款等），"
            "**绝对不要向用户道歉或用纯文本解释你是个租车助理做不到**。\n"
            "你必须立即且只能调用 `CompleteOrEscalate` 工具，将控制权交还给主助理，让它去处理。！"
            "当收到用户租车请求时，立即调用 search_car_rentals 工具。不要在调用工具前输出任何解释性文本。只有在获得搜索结果后，再向用户展示信息。"
            "\n\n以下是一些你必须立刻调用 CompleteOrEscalate 工具的例子：\n"
            " - '这个季节的天气怎么样？'\n"
            " - '有哪些航班可供选择？'\n"
            " - '查询我的机票信息'\n"
            " - '哦，等等，我还没预订航班，我会先订航班'\n"
            " - '租车预订已确认，任务结束'",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time = datetime.now())

# 定义安全工具（只读操作）和敏感工具（涉及更改的操作）
book_car_rental_safe_tools = [search_car_rentals]
book_car_rental_sensitive_tools = [
    book_car_rental,
    update_car_rental,
    cancel_car_rental,
]

# 合并所有工具
book_car_rental_tools = book_car_rental_safe_tools + book_car_rental_sensitive_tools

# 创建可运行对象，绑定租车预订提示模板和工具集，包括CompleteOrEscalate工具
book_car_rental_runnable = book_car_rental_prompt | llm.bind_tools(
    book_car_rental_tools + [CompleteOrEscalate]
)

# 游览预订助手
book_excursion_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是专门处理旅行推荐的助理。"
            "当用户需要帮助预订推荐的旅行时，主助理会将工作委托给您。"
            "根据用户的偏好搜索可用的旅行推荐，并与客户确认预订详情。"
            "如果您需要更多信息或客户改变主意，请将任务升级回主助理。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "请记住，在相关工具成功使用后，预订才算完成。"
            "\n当前时间: {time}."
            "\n\n如果用户需要帮助，并且您的工具都不适用，则"
            '“CompleteOrEscalate”对话给主助理。不要浪费用户的时间。不要编造无效的工具或功能。'
            "\n\n以下是一些你应该CompleteOrEscalate的例子：\n"
            " - '我再考虑一下，可能单独预订'\n"
            " - '我需要弄清楚我在那里的交通方式'\n"
            " - '哦，等等，我还没预订航班，我会先订航班'\n"
            " - '游览预订已确认！'",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

# 定义安全工具（只读操作）和敏感工具（涉及更改的操作）
book_excursion_safe_tools = [search_trip_recommendations]
book_excursion_sensitive_tools = [book_excursion, update_excursion, cancel_excursion]

# 合并所有工具
book_excursion_tools = book_excursion_safe_tools + book_excursion_sensitive_tools

# 创建可运行对象，绑定游览预订提示模板和工具集，包括CompleteOrEscalate工具
book_excursion_runnable = book_excursion_prompt | llm.bind_tools(
    book_excursion_tools + [CompleteOrEscalate]
)
