import time
import logging
import os
from typing import List, Dict, Any, Union

import httpx

from .config import MODEL_CONFIG, parse_model_id, strip_reasoning_tags

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


class _LightModel:
    """
    A single, callable LLM client using raw httpx — no LangChain dependency.
    The light-side parallel to a LangChain ``BaseChatModel``: one model, one
    OpenAI-compatible call, no fallback. Returns a plain dict.

    Build via :meth:`LightFactory.create`, not directly.
    """

    def __init__(self, model_id: str, timeout: int = 30,
                 client: httpx.Client = None, **params: Any):
        self.model_id = model_id
        self.provider, self.model_name = parse_model_id(model_id)
        self.base_url = _BASE_URLS[self.provider]
        self.timeout = timeout
        self.params = params  # default body params merged into every call
        # Reuse a shared client when given one (e.g. from LightRouter), else own it.
        self._owns_client = client is None
        self._client = client if client is not None else httpx.Client(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        api_key_env = MODEL_CONFIG[self.provider]["api_key"]
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # OpenRouter requires extra headers
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/tctsung/free-lunch-ai/"
            headers["X-Title"] = "free-lunch-ai"
        return headers

    def invoke(self, messages: Union[str, List[Dict[str, str]]],
               timeout: int = None, **kwargs) -> Dict[str, Any]:
        """
        Single OpenAI-compatible chat completion request.

        Args:
            messages: A string (converted to user message) or list of
                      {"role": "user", "content": "..."} dicts.
            timeout: Optional per-call timeout override.
            **kwargs: Extra body params (temperature, etc.), merged over the
                      model's default params.

        Returns:
            {"text": "...", "model_id": "provider::model"} (plus reasoning/raw_text if present)
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        body = {"model": self.model_name, "messages": messages, **self.params, **kwargs}

        resp = self._client.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers=self._headers(),
            timeout=timeout or self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data["choices"][0]["message"]
        content, tagged_reasoning, raw_text = strip_reasoning_tags(msg.get("content", ""))

        result = {"text": content, "model_id": self.model_id}

        # Include reasoning if provider returns it as a separate field
        if msg.get("reasoning"):
            result["reasoning"] = msg["reasoning"]
        elif tagged_reasoning:
            result["reasoning"] = tagged_reasoning
        if raw_text:
            result["raw_text"] = raw_text

        return result

    def __del__(self):
        if getattr(self, "_owns_client", False) and hasattr(self, "_client"):
            self._client.close()


class LightFactory:
    """
    Build a single callable light model from a ``provider::model`` id — the
    light-side parallel to ``LangChainFactory``, using raw httpx instead of
    LangChain. Returns plain dicts: ``{"text", "model_id", "reasoning?"}``.

    >>> model = LightFactory.create("groq::llama-3.1-8b-instant")
    >>> model.invoke("Hello!")
    {"text": "Hi there!", "model_id": "groq::llama-3.1-8b-instant"}
    """

    @staticmethod
    def create(model_id: str, **kwargs: Any) -> "_LightModel":
        return _LightModel(model_id, **kwargs)


class LightRouter:
    """
    Lightweight router using raw httpx — no LangChain dependency.
    Wraps a list of light models (built by :class:`LightFactory`) with automatic
    fallback. Returns a plain dict: {"text": "...", "model_id": "provider::model"}.

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
        # Reuse one model per model_id (shares the router's httpx client).
        self._model_cache: Dict[str, _LightModel] = {}

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
                # Retrieve the cached model | create it only once
                if model_id not in self._model_cache:
                    self._model_cache[model_id] = LightFactory.create(
                        model_id, timeout=model_timeout, client=self._client, **yaml_params
                    )
                model = self._model_cache[model_id]
                return model.invoke(messages, timeout=model_timeout, **kwargs)

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
