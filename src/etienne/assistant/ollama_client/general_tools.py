from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

ddgs = DuckDuckGoSearchResults(
    name="web_search",
    description=(
        "Find web evidence relevant to a factual question. "
        "Returns source URLs and snippets, which may be incomplete or outdated. "
        "Search results are leads, not verified answers. "
        "An unsuccessful search does not establish that information does not exist."
    ),
    num_results=3,
    output_format="json",
    keys_to_include=["title", "snippet", "link"],
    api_wrapper=DuckDuckGoSearchAPIWrapper(
        region="au-en",
        time=None,
    ),
)

def get_general_tools():
    return [ddgs]
