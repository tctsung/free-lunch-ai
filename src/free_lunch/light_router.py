import time
import logging
import os
import re
from typing import List, Dict, Any, Union

import httpx

from .config import MODEL_CONFIG

logger = logging.getLogger(__name__)

_PERMANENT_STATUS_CODES = {400, 401, 403, 404, 422}

# OpenAI-compatible base URLs per provider
_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "https://ollama.com/v1",
    "default": "https://text.pollinations.ai/openai",
    "pollinations": "https://gen.pollinations.ai/v1",
}


class LightRouter:
    """
    Lightweight router using raw httpx — no LangChain dependency.
    All providers use OpenAI-compatible /v1/chat/completions.
    Returns a plain dict: {"text": "...", "model_id": "provider::model"}.

    >>> router = LightRouter(func_name="fast", models=[...], timeout=30)
    >>> router.invoke("Hello!")
    {"text": "Hi there!", "model_id": "groq::llama-3.1-8b-instant"}
    """

    def __init__(self, func_name: str, models: List[Dict[str, Any]],
                 timeout: int = 30, global_timeout: int = 180):
        self.func_name = func_name
        self.models = models
        self.timeout = timeout
        self.global_timeout = global_timeout
        self._client = httpx.Client(timeout=timeout)

    def invoke(self, messages: Union[str, List[Dict[str, str]]], **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request with automatic fallback.

        Args:
            messages: A string (converted to user message) or list of
                      {"role": "user", "content": "..."} dicts.
            **kwargs: Extra params passed to the request body (temperature, etc.)

        Returns:
            {"text": "...", "model_id": "provider::model"}
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        start_time = time.time()
        active_models = list(range(len(self.models)))
        current_idx = 0
        consecutive_fails = 0
        errors = []
        backoff = 1

        while active_models:
            elapsed = time.time() - start_time
            if elapsed > self.global_timeout:
                break

            idx_pos = current_idx % len(active_models)
            model_idx = active_models[idx_pos]
            candidate = self.models[model_idx]
            model_id = candidate["id"]

            yaml_params = dict(candidate.get("params", {}))
            model_timeout = yaml_params.pop("timeout", self.timeout)

            try:
                logger.debug(f"Trying {model_id} (timeout={model_timeout}s)")
                result = self._call(model_id, messages, model_timeout, **yaml_params, **kwargs)
                result["model_id"] = model_id
                return result

            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                errors.append(f"{model_id}: {e}")
                logger.warning(f"Failover from {model_id}: {e}")

                status = self._get_status(e)
                if status in _PERMANENT_STATUS_CODES or status == 429:
                    reason = "rate limited" if status == 429 else "permanent error"
                    logger.warning(f"Removing {model_id} from rotation ({reason})")
                    active_models.pop(idx_pos)
                    consecutive_fails = 0
                    if not active_models:
                        break
                    current_idx = idx_pos % len(active_models)
                    continue

                current_idx = (idx_pos + 1) % len(active_models)
                consecutive_fails += 1

                if consecutive_fails >= len(active_models):
                    consecutive_fails = 0
                    remaining = self.global_timeout - (time.time() - start_time)
                    if backoff < remaining:
                        logger.debug(f"Full cycle failed, backing off {backoff}s")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 10)

        raise TimeoutError(
            f"FreeLunch '{self.func_name}' exhausted all models. "
            f"Last errors: {errors[-3:]}"
        )

    def _call(self, model_id: str, messages: List[Dict], timeout: int, **params) -> Dict[str, str]:
        """Single OpenAI-compatible chat completion request."""
        provider, model_name = model_id.strip().split("::", 1)

        base_url = _BASE_URLS.get(provider)
        if not base_url or provider not in MODEL_CONFIG:
            raise ValueError(f"Unknown provider '{provider}'")

        api_key_env = MODEL_CONFIG[provider]["api_key"]
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # OpenRouter requires extra headers
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/tctsung/free-lunch-ai/"
            headers["X-Title"] = "free-lunch-ai"

        body = {"model": model_name, "messages": messages, **params}

        resp = self._client.post(
            f"{base_url}/chat/completions",
            json=body,
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data["choices"][0]["message"]
        content = msg.get("content", "")

        result = {"text": content}

        # Include reasoning if provider returns it as a separate field
        if msg.get("reasoning"):
            result["reasoning"] = msg["reasoning"]
        elif "<think>" in content:
            match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            if match:
                result["reasoning"] = match.group(1).strip()
                result["raw_text"] = content
                result["text"] = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        return result

    @staticmethod
    def _get_status(e: Exception) -> int:
        """Extract HTTP status code from httpx or generic exceptions."""
        if isinstance(e, httpx.HTTPStatusError):
            return e.response.status_code
        for attr in ("status_code", "code"):
            val = getattr(e, attr, None)
            if isinstance(val, int):
                return val
        return 0

    def __del__(self):
        if hasattr(self, "_client"):
            self._client.close()
