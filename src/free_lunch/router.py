import time
from typing import List, Dict, Any, Optional, Sequence, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr, Field


from .llm_factory import LangChainFactory

class LangChainRouter(BaseChatModel):
    """
    A unified router that behaves exactly like a standard LangChain ChatModel.
    Supports .bind_tools(), .with_structured_output(), and Agent workflows.
    """
    
    # --- Configuration ---
    func_name: str
    models: List[Dict[str, Any]]
    
    # Mutable timeout (users can change this after init: model.timeout = 300)
    timeout: int = Field(default=180, description="Global timeout loop in seconds")
    
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
        
        consecutive_fails = 0
        total_models = len(self.models)
        errors = []

        while True:
            # Check Timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                break

            # Pick Candidate
            candidate = self.models[self._current_idx]
            model_id = candidate["id"]
            
            # YAML params (e.g. reasoning_effort, max_tokens) -> Factory
            yaml_params = candidate.get("params", {})
            
            try:
                # Retrieve the cached instance | Create it only once
                if model_id not in self._client_cache:
                    self._client_cache[model_id] = LangChainFactory.create(model_id, **yaml_params)
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

            except Exception as e:
                errors.append(f"{model_id}: {e}")
                
                # Rotate Index
                self._current_idx = (self._current_idx + 1) % total_models
                consecutive_fails += 1
                
                # Full Cycle Backoff
                if consecutive_fails >= total_models:
                    consecutive_fails = 0
                    if (time.time() - start_time) + 5 < self.timeout:
                        time.sleep(5) # pause after a full failed loop

        raise TimeoutError(f"FreeLunch '{self.func_name}' failed. Errors: {errors[-3:]}")

    @property
    def _llm_type(self) -> str:
        return "freelunch-router"
    
# class LightRouter
"""
Light unified router
"""

