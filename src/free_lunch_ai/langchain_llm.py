from typing import Literal, Any
import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI


MODEL_CONFIG = {
    "groq": {
        "class": ChatGroq,
        "env_key": "GROQ_API_KEY"
    },
    "google": {
        "class": ChatGoogleGenerativeAI,
        "env_key": "GOOGLE_API_KEY"
    }
}

class LangChainFactory:
    """
    Unified factory to build LangChain BaseChatModel objects with validation
    Example:
    >>> model = LangChainFactory.create("groq:llama-3.1-8b-instant")
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
        
        # 2. Retrieve Class
        model_class = MODEL_CONFIG[provider]["class"]
        
        # 3. Instantiate with extra args
        # We pass 'model' explicitly, and unpack everything else.
        return model_class(model=model_name, **kwargs)

    @staticmethod
    def _validate_and_parse(model_id: str):
        """Internal helper to validate format and keys."""
        # Format Check
        if model_id.count(":") != 1:
            raise ValueError(f"Invalid ID '{model_id}'. Must be 'provider:model'")
        
        provider, model = model_id.strip().split(":")
        
        # Provider Check
        if provider not in MODEL_CONFIG:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(MODEL_CONFIG.keys())}")
        
        # Key Check
        required_key = MODEL_CONFIG[provider]["env_key"]
        if required_key not in os.environ:
            raise ValueError(f"Missing API Key. Please set {required_key} in environment.")
            
        return provider, model