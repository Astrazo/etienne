from ddgs import DDGS
from langchain.tools import tool


@tool
def search_web(query: str) -> list[dict[str, str]]:
    """Search the web for current information."""
    return DDGS(timeout=10).text(
        query,
        backend="duckduckgo",
        max_results=3,
    )

def get_general_tools():
    return [
        search_web
    ]