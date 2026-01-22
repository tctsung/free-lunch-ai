from typing import Literal, Any
import os
from os import getenv
from functools import lru_cache

# 1. Update Config: Remove the heavy "func" objects and direct imports
MODEL_CONFIG = {
    "groq": {
        "api_key": "GROQ_API_KEY",
        "include_api_key": False,
        "extra_params": {}
    },
    "google": {
        "api_key": "GOOGLE_API_KEY",
        "include_api_key": True,
        "extra_params": {}
    },
    "openrouter": {
        "api_key": "OPENROUTER_API_KEY",
        "include_api_key": True,
        "extra_params": {
            "base_url": "https://openrouter.ai/api/v1",
            "default_headers": {
                "HTTP-Referer": "https://github.com/tctsung/free-lunch-ai/", 
                "X-Title": "free-lunch-ai"         
            }
        }
    }
}

class LangChainFactory:
    """
    Unified factory to build LangChain BaseChatModel objects.
    Uses lazy loading to prevent package bloat.
    >>> model = LangChainFactory.create("groq::llama-3.1-8b-instant")
    >>> model.invoke("Hello!")
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_model_class(provider: str):
        """
        Lazy loads the provider library only when needed.
        Cached so subsequent calls are instant.
        """
        if provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI
        elif provider == "openrouter":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI
        else:
            raise ValueError(f"Provider '{provider}' is not supported.")

    @staticmethod
    def create(model_id: str, **kwargs: Any):
        # 1. Parse ID
        provider, model_name = LangChainFactory._validate_and_parse(model_id)
        config = MODEL_CONFIG[provider]
        
        # 2. Get Class (Cached & Lazy)
        model_class = LangChainFactory._get_model_class(provider)
        
        # 3. Merge Params
        extra_params = config.get("extra_params", {}).copy()
        extra_params.update(kwargs)
        if config["include_api_key"]:
            extra_params["api_key"] = getenv(config["api_key"])

        # 4. Instantiate
        # Note: This creates a new connection pool every time. 
        # For a router switching between free tiers, this is acceptable.
        return model_class(model=model_name, **extra_params)

    @staticmethod
    def _validate_and_parse(model_id: str):
        """Internal helper to validate format and keys."""
        if model_id.count("::") < 1:
            raise ValueError(f"Invalid ID '{model_id}'. Must be 'provider::model'")
        
        provider, model = model_id.strip().split("::", 1)
        
        if provider not in MODEL_CONFIG:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(MODEL_CONFIG.keys())}")
        
        required_key = MODEL_CONFIG[provider]["api_key"]
        if required_key not in os.environ:
            raise ValueError(f"Missing API Key. Please set {required_key} in environment.")
            
        return provider, model
    
# class LightFactory():
"""
Unified factory to build direct api call object similar to curl
Light because have no dependencies
"""


####### Helper ########

def content_blocks_dict(content_blocks, model_id):

    # for simple text output
    if isinstance(content_blocks, str):
        return {"text": content_blocks, "model_id": model_id}

    # for langchain 1.0 standardized format
    dct = {}
    for block in content_blocks:
        key = block["type"]
        val = block.get(key)
        dct[key] = val

    if len(content_blocks) == len(dct):
        dct["model_id"] = model_id # keep track of model_id
        return dct
    logging.warning(f"Information loss in {model_id}: Duplicate content types detected.")