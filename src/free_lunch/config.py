"""
Shared configuration and utilities — no LangChain dependency.
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

_REASONING_TAGS = ("think", "thought")
_REASONING_BLOCK_TYPES = ("thinking", "reasoning")

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


def flatten_content_blocks(content: Any) -> tuple[str, str | None]:
    """Split block-based message content into visible text and reasoning."""
    if isinstance(content, str):
        return content, None

    text_parts = []
    reasoning_parts = []

    for block in content:
        if not isinstance(block, dict):
            text_parts.append(str(block))
            continue

        block_type = block.get("type", "")
        if block_type in _REASONING_BLOCK_TYPES:
            reasoning_text = block.get(block_type) or block.get("thinking") or block.get("reasoning") or block.get("text")
            if reasoning_text:
                reasoning_parts.append(str(reasoning_text))
            continue

        block_text = block.get("text") or block.get(block_type)
        if block_text:
            text_parts.append(str(block_text))

    reasoning = "\n".join(reasoning_parts).strip() or None
    text = "\n".join(text_parts).strip()
    return text, reasoning


def strip_reasoning_tags(content: str) -> tuple[str, str | None, str | None]:
    """Remove tagged reasoning from text while preserving it separately."""
    for tag in _REASONING_TAGS:
        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            continue

        reasoning = match.group(1).strip() or None
        stripped = re.sub(pattern, "", content, flags=re.DOTALL).strip()
        return stripped, reasoning, content

    return content, None, None


def _latest_message(response):
    """Return the final AI-like message from an AIMessage, agent state, or message list."""
    if isinstance(response, dict):
        messages = response.get("messages")
        if messages:
            return _latest_message(messages)
        return response

    if isinstance(response, (list, tuple)):
        for message in reversed(response):
            if message.__class__.__name__ == "AIMessage":
                return message
        return response[-1] if response else None

    return response


def content_blocks_dict(response, include_raw: bool = True):
    """
    Flatten a LangChain AIMessage or agent response into a simple dict.
    >>> response = llm.invoke("hello")
    >>> content_blocks_dict(response)
    {"text": "Hello!", "model_id": "groq::llama-3.1-8b-instant"}
    >>> raw_response = agent.invoke({"messages": [...]})
    >>> content_blocks_dict(raw_response)["text"]
    "Final answer..."
    >>> result = content_blocks_dict(raw_response, include_raw=True)
    >>> result["raw_response"] is raw_response
    True
    """
    raw_response = response
    response = _latest_message(response)
    if response is None:
        result = {"model_id": "unknown", "text": ""}
        if include_raw:
            result["raw_response"] = raw_response
        return result

    if isinstance(response, dict):
        result = {
            "model_id": response.get("model_id", "unknown"),
            "text": response.get("text") or response.get("content") or "",
        }
        if include_raw:
            result["raw_response"] = raw_response
        return result

    response_metadata = getattr(response, "response_metadata", {}) or {}
    model_id = response_metadata.get("model_id", "unknown")
    content = getattr(response, "content", "")
    result = {"model_id": model_id}
    if include_raw:
        result["raw_response"] = raw_response

    # Include reasoning if provider returns it as a separate field
    additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
    reasoning = additional_kwargs.get("reasoning") or additional_kwargs.get("reasoning_content")
    if reasoning:
        result["reasoning"] = reasoning

    content, block_reasoning = flatten_content_blocks(content)
    if block_reasoning and "reasoning" not in result:
        result["reasoning"] = block_reasoning

    content, tagged_reasoning, raw_text = strip_reasoning_tags(content)
    if tagged_reasoning and "reasoning" not in result:
        result["reasoning"] = tagged_reasoning
    if raw_text:
        result["raw_text"] = raw_text

    result["text"] = content
    return result
