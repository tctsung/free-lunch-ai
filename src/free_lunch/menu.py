import os
import yaml
from functools import partial
from typing import Any, Dict
from dotenv import load_dotenv
from os import getenv
import warnings

# package import
from router import LangChainRouter
# from light_router import LightRouter

# Map Environment Variable names to provider prefix in yaml
PROVIDER_MAPPING = {
    "GROQ_API_KEY": "groq",
    "GOOGLE_API_KEY": "google",
    "OPENROUTER_API_KEY": "openrouter"
}

def _load_api_keys(env_path: str = None) -> set:
    """
    Loads .env and returns a set of available provider names (e.g. {'groq', 'google'}).
    """
    # 1. Load Environment
    if env_path:
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)

    # 2. Check availability
    available_providers = set()
    for env_key, provider_name in PROVIDER_MAPPING.items():
        if os.getenv(env_key):
            available_providers.add(provider_name)
            
    return available_providers

class Menu:
    """
    A dynamic factory that transforms a YAML configuration file into executable model routers.

    Example:
    >>> menu = Menu("menu.yaml", env_path=".env")
    >>> router = menu.fast(timeout=30)  # Creates router defined under key 'fast'
    >>> router.invoke("Hello")
    """
    
    def __init__(self, yaml_path: str, env_path: str = None):
        # get set of existing providers
        self.available_providers = _load_api_keys(env_path)
        
        # load & validate yaml file info
        self.yaml_path = yaml_path
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        with open(yaml_path, 'r') as f:
            self.yaml_content = yaml.safe_load(f) or {}
        self._validate_yaml()

    def _validate_yaml(self):
        """
        1. Checks that YAML keys do not shadow class methods.
        2. Checks yaml keys are valid
        """
        reserved_names = set(dir(self))
        valid_types = {"langchain", "light"}
        
        for key, config in self.yaml_content.items():
            # Check 1: Reserved Keywords
            if key in reserved_names:
                raise ValueError(
                    f"YAML Conflict: Key '{key}' reserves an internal function name. "
                    f"Please rename '{key}' in {self.yaml_path}."
                )
            
            # Check 2: Type Validation
            model_type = config.get("type")
            if model_type not in valid_types:
                raise ValueError(
                    f"Invalid type for '{key}': Found '{model_type}'. "
                    f"Must be one of {valid_types}."
                )
            
            original_models = config.get("models", [])
            valid_models = []
            invalid_ids = []
            removed_cnt = 0
            for m in original_models:
                model_id = m.get("id", "")
                
                # Check 3: all ids must include one `::`
                if "::" not in model_id:
                    invalid_ids.append(model_id)
                    continue  # Skip further checks for broken ID

                # Check 4: API key Availability
                provider = model_id.split("::")[0]
                if provider in self.available_providers:
                    valid_models.append(m)
                else:
                    removed_cnt += 0
            
            # update valid model list:
            config["models"] = valid_models

            # status update:
            if len(invalid_ids) > 0:
                raise ValueError(
                    f"{len(invalid_ids)} invalid models id detected in {self.yaml_path}."
                    f"List of failed ids (must be `provider::model`): {invalid_ids}"
                    )
            if removed_cnt > 0:
                warnings.warn(
                    f"{removed_cnt} model ids were removed due to missing API keys.\nExisting api key providers: {self.available_providers}",
                    UserWarning,
                    stacklevel=2
                    )


    def _create_langchain_router(self, func_name: str, timeout: int = 180):
        """Builder for heavy LangChain routers"""
        config = self.yaml_content[func_name]
        return LangChainRouter(
            func_name=func_name,
            models=config.get("models", []),
            timeout=timeout
        )

    def _create_light_router(self, func_name: str, timeout: int = 180):
        """Builder for lightweight/fast routers (Placeholder)"""
        config = self.yaml_content[func_name]
        # Placeholder:
        raise NotImplementedError(f"Light router for '{func_name}' is not yet implemented.")

    def __getattr__(self, name: str):
        """
        Dynamic Dispatcher:
        1. Checks if name exists in YAML file key
        3. Returns the correct partial function based on model type
        """
        if name not in self.yaml_content:
            raise AttributeError(f"Menu item '{name}' not found in {self.yaml_path}")

        # Retrieve configuration
        config = self.yaml_content[name]
        router_type = config.get("type")

        # 1. Model router based on 'type'
        if router_type == "langchain":
            return partial(self._create_langchain_router, func_name=name)
        elif router_type == "light":
            return partial(self._create_light_router, func_name=name)

        # fallback
        raise ValueError(f"Unknown router type '{router_type}' for '{name}'")
    def __dir__(self):
        """
        Add dynamic YAML keys into method dir, helps IDE autocomplete
        """
        # Start with standard class methods
        base_attrs = set(super().__dir__())
        
        # Add our dynamic YAML keys
        dynamic_attrs = set(self.yaml_content.keys())
        
        return list(base_attrs | dynamic_attrs)