from typing import Literal, Any
import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from os import getenv
import logging
# lookup table:

MODEL_CONFIG = {
    "groq": {
        "func": ChatGroq,
        "api_key": "GROQ_API_KEY",
        "include_api_key": False,   # if include_api_key=T, will add as a **kwrg
        "extra_params": {}
    },
    "google": {
        "func": ChatGoogleGenerativeAI,
        "api_key": "GOOGLE_API_KEY",
        "include_api_key": True,
        "extra_params": {}
    },
    "openrouter": {
        "func": ChatOpenAI,
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
    Unified factory to build LangChain BaseChatModel objects with validation
    Example:
    >>> model = LangChainFactory.create("groq::llama-3.1-8b-instant")
    >>> model.invoke("Hello!")
    """

    @staticmethod
    def create(model_id: str, **kwargs: Any):
        """
        Creates and returns a ready-to-use LangChain ChatModel

        Args:
            model_id: Format 'provider:model' (e.g., 'groq:llama3-8b-8192')
            **kwargs: Extra arguments passed directly to the model constructor 
                      (e.g., temperature=1.0, max_retries=2, max_tokens=8192).
        
        Returns:
            A BaseChatModel instance (ChatGroq, ChatGoogleGenerativeAI, etc.)
        """
        # 1. Parse & Validate
        provider, model_name = LangChainFactory._validate_and_parse(model_id)
        config = MODEL_CONFIG[provider]
        # 2. Retrieve function
        model_func = config["func"]
        
        # 3. prioritize input kwargs over extra_parameters
        extra_params = config.get("extra_params", {}).copy()
        extra_params.update(kwargs)
        if config["include_api_key"]:
            extra_params["api_key"] = getenv(config["api_key"])

        # 3. Instantiate model 
        return model_func(model=model_name, **extra_params)

    @staticmethod
    def _validate_and_parse(model_id: str):
        """Internal helper to validate format and keys."""
        # Format Check
        if model_id.count("::") < 1:
            raise ValueError(f"Invalid ID '{model_id}'. Must be 'provider::model'")
        
        provider, model = model_id.strip().split("::", 1)
        
        # Provider Check
        if provider not in MODEL_CONFIG:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(MODEL_CONFIG.keys())}")
        
        # Key Check
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