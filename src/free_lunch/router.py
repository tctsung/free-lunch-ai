import time
from typing import List, Dict, Any, Optional, Sequence, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr, Field


from llm_factory import LangChainFactory

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

    # --- 1. Tool Binding Support ---
    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Optional[Union[dict, str]] = None,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        """
        Stores tools/args in the config so they appear in _generate's kwargs later.
        Required for .with_structured_output() to work.
        """
        return self.bind(tools=tools, tool_choice=tool_choice, **kwargs)

    # --- 2. The Execution Loop ---
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
        # When .bind_tools() is used, 'tools' and 'tool_choice' arrive in kwargs.
        # We need to extract them to bind to the inner model explicitly.
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
                # B. Create the REAL Model (Lazy)
                # We pass YAML params here (e.g. temperature defined in yaml)
                llm = LangChainFactory.create(model_id, **yaml_params)

                # C. Re-Bind Tools (The Critical Step)
                # If tools were passed to this router, we must pass them down.
                if tools:
                    # We call bind_tools on the inner ChatGroq/ChatGemini object.
                    # This handles the provider-specific formatting (OpenAI vs Google format).
                    llm = llm.bind_tools(tools, tool_choice=tool_choice)

                # D. Invoke
                # We pass the remaining kwargs (like run_id, callbacks, or extra invoke-time args)
                # AND any 'stop' sequences.
                response_msg = llm.invoke(messages, stop=stop, **kwargs)

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
                    if (time.time() - start_time) + 2 < self.timeout:
                        time.sleep(2) # Prevent hammering APIs
            finally:
                # Force cleanup to ensure httpx client inside 'llm' is marked for deletion
                if llm:
                    del llm

        raise TimeoutError(f"FreeLunch '{self.func_name}' failed. Errors: {errors[-3:]}")

    @property
    def _llm_type(self) -> str:
        return "freelunch-router"
    
# class LightRouter
"""
Light unified router
"""

