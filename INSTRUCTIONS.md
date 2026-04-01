# INSTRUCTIONS.md — Developer Reference

## What This Project Does

A router for free-tier LLM APIs. One YAML config, one entrypoint (`Menu`), automatic fallback across providers (Groq, Gemini, OpenRouter, Ollama). Two router modes: **LangChain** (full ecosystem compat) and **Light** (raw httpx, zero heavy deps).

## Install Tiers

```
pip install git+...                          # light only (httpx, pyyaml, dotenv, pydantic)
pip install "free-lunch-ai[langchain] @ ..." # + langchain-core, langchain-groq, langchain-google-genai, langchain-openai
pip install "free-lunch-ai[all] @ ..."       # everything
```

## Architecture

```
src/free_lunch/
├── config.py          # SHARED: MODEL_CONFIG, content_blocks_dict()
├── defaults.py        # SHARED: DEFAULT_MENU (fast/think/agent model lists)
├── menu.py            # SHARED: Menu class — YAML loader, validator, dispatcher
├── light_router.py    # LIGHT:  LightRouter — raw httpx POST, returns dict
├── llm_factory.py     # LC:     LangChainFactory — builds ChatGroq/ChatOpenAI/etc
├── router.py          # LC:     LangChainRouter — extends BaseChatModel, returns AIMessage
└── __init__.py        # Public exports, try/except for langchain imports
```

### Dependency Graph

```
config.py  ←── light_router.py                    (light install)
config.py  ←── llm_factory.py ←── router.py       (langchain install)
defaults.py ←── menu.py ──→ light_router.py        (always)
                         ──→ router.py              (try/except, optional)
```

## File Details

### `config.py` — Shared config (no heavy deps)
- `MODEL_CONFIG`: dict mapping provider name → API key env var, default params, base URLs
- `content_blocks_dict(response)`: flattens LangChain AIMessage → `{"text", "model_id", "reasoning?", "raw_text?"}`
- To add a new provider: add entry here + add base URL in `light_router._BASE_URLS`

### `defaults.py` — Zero-config presets
- `DEFAULT_MENU`: model lists for `fast`, `think`, `agent`
- No `type` field — set dynamically by `Menu.__init__()` based on installed packages
- Models ordered by: quality-per-latency first, Groq → Gemini Flash → Ollama → OpenRouter → Gemini Pro

### `menu.py` — Orchestrator
- `Menu(yaml_path=None, env_path=None)`: loads YAML or defaults, loads .env, validates
- Auto-detects `type: langchain` vs `type: light` for defaults based on whether LangChain is installed
- `_validate_yaml()`: checks reserved names, valid types, model ID format (`provider::model`), strips models with missing API keys
- `__getattr__`: dynamic dispatch — `menu.fast()` returns a router based on YAML config
- Raises clear `ImportError` if `type: langchain` used without langchain installed

### `light_router.py` — Light router (httpx only)
- `LightRouter.invoke(messages, **kwargs)` → `{"text", "model_id", "reasoning?", "raw_text?"}`
- Accepts string or `[{"role": "user", "content": "..."}]` message format
- `_call()`: single httpx POST to `{base_url}/chat/completions` with Bearer auth
- `_BASE_URLS`: OpenAI-compatible endpoints per provider
- Reasoning: extracts `message.reasoning` field OR `<think>` tags → `reasoning` key, strips from `text`, keeps `raw_text`

### `llm_factory.py` — LangChain factory (requires langchain)
- `LangChainFactory.create(model_id, **kwargs)` → `BaseChatModel` instance
- `_get_model_class()`: lazy imports with `@lru_cache` — provider libs loaded only when first used
- Merges `MODEL_CONFIG.extra_params` + user kwargs → passes to constructor

### `router.py` — LangChain router (requires langchain)
- Extends `BaseChatModel` — drop-in replacement for any LangChain chat model
- Supports `.bind_tools()`, `.with_structured_output()`, agent workflows
- `_generate()`: fallback loop with per-model + global timeouts
- `_client_cache`: reuses `BaseChatModel` instances across calls (connection pooling)
- Injects `model_id` into `response.response_metadata["model_id"]`

### Shared Fallback Logic (both routers)
- Models tried top-to-bottom from YAML/defaults
- **429 rate limit**: model dropped from rotation for current request (not permanently)
- **Permanent errors** (400, 401, 403, 404, 422): model dropped permanently
- **Other errors**: rotate to next, exponential backoff (1s→2s→4s→10s cap) after full cycle
- `max_retries=0` on all providers — router owns all retry logic, no hidden SDK retries

## Key Design Decisions

1. **`max_retries=0`** on all LangChain providers — prevents hidden SDK retries that compound latency (e.g., Gemini 429 taking 57s instead of ~15s)
2. **429 drops from rotation** per-request, not permanently — model may work on next `.invoke()` call
3. **Gemini models last in defaults** — lowest free-tier quotas (5-15 RPM), long server-side waits before 429
4. **Ollama uses ChatOpenAI** (langchain) / raw httpx (light) — OpenAI-compatible at `https://ollama.com/v1/`, no extra dependency
5. **`DEFAULT_MENU` has no `type` field** — set at runtime by `Menu` based on installed packages

## Adding a New Provider

1. `config.py`: add to `MODEL_CONFIG` (api_key env var, include_api_key, extra_params)
2. `light_router.py`: add to `_BASE_URLS` (OpenAI-compatible base URL)
3. `llm_factory.py`: add to `_get_model_class()` (lazy import of LangChain class)
4. `menu.py`: add to `PROVIDER_MAPPING` (env var → provider name)
5. `doc/models.md`: add model reference section
6. `examples/.env.example`: add env var placeholder

## Testing

```bash
python tests/test_connections.py   # tests each provider × both router types
```
Skips providers without API keys. Tests individual providers + fallback across all.

## Git Guidelines

Ensure `git remote set-url origin git@github.com:tctsung/free-lunch-ai.git` is set before push code



