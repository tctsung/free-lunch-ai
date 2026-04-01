"""
LangChain model factory — requires langchain packages.
"""
from typing import Any
import os
from os import getenv
from functools import lru_cache

from .config import MODEL_CONFIG


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
        elif provider == "ollama":
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
