from langchain_community.tools import DuckDuckGoSearchResults
def get_general_tools():
    return [DuckDuckGoSearchResults()]
