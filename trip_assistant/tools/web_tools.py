from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# 实例化基础的搜索工具
search = DuckDuckGoSearchRun()

@tool
def web_search(query: str) -> str:
    """
    当用户询问实时的天气、景点信息、时事新闻、或者你数据库里没有的通用旅行攻略时，使用此工具。
    :param query: 搜索关键词，例如 '巴黎 明天 天气' 或 '上海迪士尼 最新门票价格'
    """
    try:
        # 调用 DuckDuckGo 执行搜索并返回结果片段
        result = search.invoke(query)
        return result
    except Exception as e:
        return f"搜索失败，错误信息: {str(e)}"