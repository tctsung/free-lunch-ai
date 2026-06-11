# Shared (always available)
from .menu import Menu
from .light_router import LightRouter, LightFactory
from .config import content_blocks_dict, MODEL_CONFIG
from .defaults import DEFAULT_MENU
from .tools import (
    build_langchain_tools,
    current_time,
    fetch_url,
    read_file,
    web_search,
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
    "LightFactory",
    "LangChainRouter",
    "LangChainFactory",
    "MODEL_CONFIG",
    "DEFAULT_MENU",
    "content_blocks_dict",
    "web_search",
    "fetch_url",
    "current_time",
    "read_file",
    "build_langchain_tools",
]
