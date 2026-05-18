# Shared (always available)
from .menu import Menu
from .light_router import LightRouter
from .config import content_blocks_dict, MODEL_CONFIG
from .defaults import DEFAULT_MENU
from .tools import (
    build_langchain_tools,
    current_time,
    current_time_tool,
    fetch_url,
    fetch_url_tool,
    web_search,
    web_search_tool,
)

# LangChain (optional)
try:
    from .router import LangChainRouter
    from .llm_factory import LangChainFactory
except ImportError:
    LangChainRouter = None
    LangChainFactory = None

__all__ = [
    "Menu", 
    "LightRouter",
    "LangChainRouter",
    "LangChainFactory",   
    "MODEL_CONFIG",
    "DEFAULT_MENU",
    "content_blocks_dict",
    "web_search",
    "fetch_url",
    "current_time",
    "web_search_tool",
    "fetch_url_tool",
    "current_time_tool",
    "build_langchain_tools",
]
