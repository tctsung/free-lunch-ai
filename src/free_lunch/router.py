import time
import logging
from typing import List, Dict, Any, Optional, Sequence, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr, Field


from .llm_factory import LangChainFactory

logger = logging.getLogger(__name__)

# HTTP status codes that indicate permanent (non-retryable) failures
_PERMANENT_STATUS_CODES = {400, 401, 403, 404, 422}

class LangChainRouter(BaseChatModel):
    """
    A unified router that behaves exactly like a standard LangChain ChatModel.
    Supports .bind_tools(), .with_structured_output(), and Agent workflows.
    """
    
    # --- Configuration ---
    func_name: str
    models: List[Dict[str, Any]]
    
    # Per-model timeout: max seconds to wait for a single API call (default 30s)
    timeout: int = Field(default=30, description="Per-model request timeout in seconds")
    
    # Global timeout: total seconds before giving up on the entire fallback loop (default 180s)
    global_timeout: int = Field(default=180, description="Total timeout budget for all retries")
    
    # Sticky session index (private)
    _current_idx: int = PrivateAttr(default=0)
    
    # cache BaseChatModel to reuse TCP/SSL connections
    # key:val =  'provider::model': BaseChatModel
    _client_cache: Dict[str, BaseChatModel] = PrivateAttr(default_factory=dict)

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Optional[Union[dict, str]] = None,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        """
        Stores tools/args in the config so they appear in _generate's kwargs later
        """
        return self.bind(tools=tools, tool_choice=tool_choice, **kwargs)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Intercepts the call, routes to underlying models, and handles failover.
        """
        start_time = time.time()
        
        # A. Separate Tooling Args from Runtime Args
        tools = kwargs.pop("tools", None)
        tool_choice = kwargs.pop("tool_choice", None)
        
        # Reset to preferred model (#0) at the start of each call
        self._current_idx = 0
        
        consecutive_fails = 0
        active_models = list(range(len(self.models)))  # indices of models still in rotation
        errors = []
        backoff = 1  # exponential backoff starting at 1s

        while active_models:
            # Check Global Timeout
            elapsed = time.time() - start_time
            if elapsed > self.global_timeout:
                break

            # Pick Candidate
            idx_pos = self._current_idx % len(active_models)
            model_idx = active_models[idx_pos]
            candidate = self.models[model_idx]
            model_id = candidate["id"]
            
            # Per-model timeout: params.timeout > profile timeout > default 30s
            yaml_params = dict(candidate.get("params", {}))
            model_timeout = yaml_params.pop("timeout", self.timeout)
            
            try:
                logger.debug(f"Trying {model_id} (timeout={model_timeout}s)")
                
                # Retrieve the cached instance | Create it only once
                if model_id not in self._client_cache:
                    self._client_cache[model_id] = LangChainFactory.create(
                        model_id, timeout=model_timeout, **yaml_params
                    )
                base_llm = self._client_cache[model_id]

                # applies tools just for this request.
                if tools:
                    invokable_llm = base_llm.bind_tools(tools, tool_choice=tool_choice)
                else:
                    invokable_llm = base_llm

                # pass the remaining kwargs
                response_msg = invokable_llm.invoke(messages, stop=stop, **kwargs)

                # E. Inject ID for debugging
                response_msg.response_metadata["model_id"] = model_id
                
                return ChatResult(generations=[ChatGeneration(message=response_msg)])

            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                errors.append(f"{model_id}: {e}")
                logger.warning(f"Failover from {model_id}: {e}")
                
                # Check if error is non-retryable for this request
                if self._is_permanent_error(e) or self._is_rate_limit(e):
                    reason = "permanent error" if self._is_permanent_error(e) else "rate limited"
                    logger.warning(f"Removing {model_id} from rotation ({reason})")
                    active_models.pop(idx_pos)
                    consecutive_fails = 0
                    if not active_models:
                        break
                    self._current_idx = idx_pos % len(active_models)
                    continue
                
                # Rotate Index
                self._current_idx = (idx_pos + 1) % len(active_models)
                consecutive_fails += 1
                
                # Full Cycle Backoff (exponential: 1s, 2s, 4s, capped at 10s)
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
    def _is_rate_limit(e: Exception) -> bool:
        """Check if error is a 429 rate limit."""
        for attr in ("status_code", "code"):
            if getattr(e, attr, None) == 429:
                return True
        resp = getattr(e, "response", None)
        if resp and getattr(resp, "status_code", None) == 429:
            return True
        return False

    @staticmethod
    def _is_permanent_error(e: Exception) -> bool:
        """Check if an error is non-retryable based on HTTP status code."""
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        if isinstance(status, int) and status in _PERMANENT_STATUS_CODES:
            return True
        # Check nested httpx/requests response
        response = getattr(e, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
            if isinstance(status, int) and status in _PERMANENT_STATUS_CODES:
                return True
        return False

    @property
    def _llm_type(self) -> str:
        return "freelunch-router"

