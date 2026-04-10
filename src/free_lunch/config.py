"""
Shared configuration and utilities — no LangChain dependency.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Provider configuration: API key env vars and default params
MODEL_CONFIG = {
    "groq": {
        "api_key": "GROQ_API_KEY",
        "include_api_key": False,
        "extra_params": {"max_retries": 0}
    },
    "google": {
        "api_key": "GOOGLE_API_KEY",
        "include_api_key": True,
        "extra_params": {"max_retries": 0}
    },
    "openrouter": {
        "api_key": "OPENROUTER_API_KEY",
        "include_api_key": True,
        "extra_params": {
            "max_retries": 0,
            "base_url": "https://openrouter.ai/api/v1",
            "default_headers": {
                "HTTP-Referer": "https://github.com/tctsung/free-lunch-ai/", 
                "X-Title": "free-lunch-ai"         
            }
        }
    },
    "ollama": {
        "api_key": "OLLAMA_API_KEY",
        "include_api_key": True,
        "extra_params": {
            "max_retries": 0,
            "base_url": "https://ollama.com/v1/"
        }
    },
    "default": {
        "api_key": None,
        "include_api_key": False,
        "extra_params": {
            "max_retries": 0,
            "base_url": "https://text.pollinations.ai/openai",
            "api_key": "dummy",  # ChatOpenAI requires non-empty api_key; not sent to server
        }
    },
    "pollinations": {
        "api_key": "POLLINATIONS_API_KEY",
        "include_api_key": True,
        "extra_params": {
            "max_retries": 0,
            "base_url": "https://gen.pollinations.ai/v1",
        }
    }
}


def content_blocks_dict(response):
    """
    Flatten a LangChain AIMessage into a simple dict.
    >>> response = llm.invoke("hello")
    >>> content_blocks_dict(response)
    {"text": "Hello!", "model_id": "groq::llama-3.1-8b-instant"}
    """
    model_id = response.response_metadata.get("model_id", "unknown")
    content = response.content
    result = {"model_id": model_id}

    # Include reasoning if provider returns it as a separate field
    reasoning = getattr(response, "additional_kwargs", {}).get("reasoning")
    if reasoning:
        result["reasoning"] = reasoning

    # Flatten content blocks list to string
    if not isinstance(content, str):
        parts = [block.get(block.get("type", ""), str(block)) if isinstance(block, dict) else str(block)
                 for block in content]
        content = "\n".join(parts)

    # Extract <think> tags: strip from text, keep raw_text as safety net
    if "reasoning" not in result and "<think>" in content:
        match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
        if match:
            result["reasoning"] = match.group(1).strip()
            result["raw_text"] = content
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    result["text"] = content
    return result
