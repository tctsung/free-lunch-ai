# INSTRUCTIONS.md — Developer Reference

## What This Project Does

A router for free-tier LLM APIs. One YAML config, one entrypoint (`Menu`), automatic fallback across providers (Groq, Gemini, OpenRouter, Ollama). Two router modes: **LangChain** (full ecosystem compat) and **Light** (raw httpx, zero heavy deps).

## Install Tiers

```
pip install git+...                          # light/base install (routers + ddgs helpers)
pip install "free-lunch-ai[langchain] @ ..." # + langchain-core, langchain-groq, langchain-google-genai, langchain-openai
pip install "free-lunch-ai[rag] @ ..."       # + pdfplumber, mammoth, openpyxl, markdownify (read_file: PDF/DOCX/XLSX/HTML -> md)
pip install "free-lunch-ai[all] @ ..."       # everything (langchain + rag)
```

## Local Dev Environment (uv)

Use [uv](https://docs.astral.sh/uv/) for local development — it reads `.python-version` (3.11) and resolves fast.

```bash
uv venv                      # create .venv at repo root
uv pip install -e ".[all]"   # editable install, every feature available
source .venv/bin/activate    # then run python / tests directly
```

- `pyproject.toml` is the source of truth for dependency **ranges**; `[all]` pulls in the `langchain` + `rag` extras.
- `requirements.txt` is a fully-pinned lock generated from it — regenerate after changing deps:
  ```bash
  uv pip compile pyproject.toml --extra all -o requirements.txt
  ```
- `.venv/` is git-ignored. No lockfile (`uv.lock`) is committed: this is a library, so consumers resolve against the published ranges rather than our pins.

## Architecture

```
src/free_lunch/
├── config.py          # SHARED: MODEL_CONFIG, content_blocks_dict()
├── defaults.py        # SHARED: DEFAULT_MENU (fast/think/agent model lists)
├── menu.py            # SHARED: Menu class — YAML loader, validator, dispatcher
├── light_router.py    # LIGHT:  LightFactory (single call) + LightRouter (fallback); _LightModel private
├── llm_factory.py     # LC:     LangChainFactory — builds ChatGroq/ChatOpenAI/etc
├── router.py          # LC:     LangChainRouter — extends BaseChatModel, returns AIMessage
├── tools.py           # SHARED/LC: plain functions + optional LangChain tool wrappers
└── __init__.py        # Public exports, try/except for langchain imports
```

### Dependency Graph

```
config.py  ←── light_router.py                    (light install)
config.py  ←── llm_factory.py ←── router.py       (langchain install)
ddgs       ←── tools.py                           (light install)
langchain  ←── tools.py                           (optional wrappers)
defaults.py ←── menu.py ──→ light_router.py        (always)
                         ──→ router.py              (try/except, optional)
```

## File Details

### `config.py` — Shared config (no heavy deps)
- `MODEL_CONFIG`: dict mapping provider name → API key env var, default params, base URLs
- `parse_model_id(model_id)`: single source of truth for the `provider::model` format — splits and validates against `MODEL_CONFIG`. Used by both `LangChainFactory` and `_LightModel`; each adds its own extra check on top (LangChain verifies the key is set, light reads it lazily)
- `strip_reasoning_tags(content)`: internal helper that removes tagged reasoning from visible text while preserving it separately
- `flatten_content_blocks(content)`: internal helper that separates visible text blocks from reasoning/thinking blocks
- `content_blocks_dict(response)`: public helper that flattens LangChain AIMessage or create_agent response dict → `{"text", "model_id", "reasoning?", "raw_text?"}`
- To add a new provider: add entry here + add base URL in `light_router._BASE_URLS`

### `defaults.py` — Zero-config presets
- `DEFAULT_MENU`: model lists for `fast`, `think`, `agent`
- No `type` field — set dynamically by `Menu.__init__()` based on installed packages
- Models ordered by: practical default priority for zero-config use, with current live model IDs and fast/strong fallbacks
- `agent` preset prioritizes provider-native tool systems first, then strong tool-calling / agent-oriented models

### `menu.py` — Orchestrator
- `Menu(yaml_path=None, env_path=None)`: loads YAML or defaults, loads .env, validates
- Auto-detects `type: langchain` vs `type: light` for defaults based on whether LangChain is installed
- `_validate_yaml()`: checks reserved names, valid types, model ID format (`provider::model`), strips models with missing API keys
- `__getattr__`: dynamic dispatch — `menu.fast()` returns a router based on YAML config
- Raises clear `ImportError` if `type: langchain` used without langchain installed

### `tools.py` — Built-in tools and helpers
- `web_search(query, max_results=5)` → `list[{"title", "url", "snippet"}]`
- `fetch_url(url)` → `{"url", "content"}`. **Jina-first**: tries the keyless [Jina Reader](https://jina.ai/reader/) (`_fetch_jina`) first because it renders pages in a real browser server-side, returning full content for JS/SPA sites (e.g. Airbnb) that plain extraction sees as empty/stub. On any `httpx.HTTPError` (most often Jina's ~20 req/min keyless limit) it falls back to unlimited DDGS extraction. Cost: Jina is ~2× slower and routes URLs through a third party — the design favors content completeness
- `current_time(timezone=None)` → `{"date", "weekday", "time", "timezone"}`
- `read_file(path)` → `{"path", "content", "format"}`. Local file → Markdown for RAG. Dispatches by suffix: `.pdf` (pdfplumber, pages joined as `## Page N`), `.docx` (mammoth → markdown), `.xlsx` (openpyxl, one Markdown table per sheet under `## SheetName`; empty sheets skipped, ragged rows padded, pipes escaped via `_md_cell`), `.html`/`.htm` (markdownify); plain-text suffixes (`_PLAIN_TEXT_SUFFIXES`: md/txt/csv/tsv/json/xml) returned verbatim. Parsers lazy-imported via `_require()` and raise a `[rag]`-extra `ImportError` if missing. `FileNotFoundError` for missing files, `ValueError` for unsupported suffixes. Fully local, no ML deps
- `build_langchain_tools(*functions)` → wraps plain functions into ready-to-bind LangChain tools (requires `langchain-core`); call with no args to build all four, or pass specific functions for a subset. Raises `ImportError` if LangChain is absent
- Internal `_tool_*` helpers render LLM-friendly string output that `build_langchain_tools` wraps; they are not part of the public API
- Uses DDGS markdown extraction by default for page fetches

### `light_router.py` — Light factory + router (httpx only)
- `LightFactory.create(model_id, **kwargs)` → a single callable light model — the light-side parallel to `LangChainFactory.create()` (which returns a `BaseChatModel`). `.invoke(messages, timeout=None, **kwargs)` → `{"text", "model_id", "reasoning?", "raw_text?"}`. One OpenAI-compatible POST to `{base_url}/chat/completions`, no fallback. `params` (and per-call `kwargs`) merge into the request body
- `_LightModel` (private — build via `LightFactory.create`, never directly): the actual client class. Owns its own httpx client unless one is passed in (`_owns_client` guards `__del__` so a shared client isn't double-closed). Parses the id via the shared `config.parse_model_id`
- `LightRouter.invoke(messages, **kwargs)` → same dict, with automatic fallback across `models`. Caches one model per id in `_model_cache` (built via `LightFactory.create`), all sharing the router's httpx client (connection pooling) — the light parallel to `LangChainRouter._client_cache`
- Accepts string or `[{"role": "user", "content": "..."}]` message format
- `_BASE_URLS`: OpenAI-compatible endpoints per provider
- Reasoning: extracts `message.reasoning`, tagged reasoning (`<think>`, `<thought>`), and structured thinking blocks into the `reasoning` key while keeping visible answer text clean

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
python -m unittest tests/test_web_tools.py
python -m unittest tests/test_content_blocks.py
```
Test behavior:

- Loads `examples/.env` first, then repo-root `.env`
- Skips providers without API keys
- Tests one small/fast current model per configured provider
- Exercises both `LightRouter` and LangChain router paths
- Runs an all-provider fallback smoke test
- Uses mocked tests for built-in tools and response parsing (no live network required)
- `test_connections.py` output includes the responding `model_id` — useful for spotting stale model IDs and provider-specific auth issues

## Git Guidelines

Ensure `git remote set-url origin git@github.com:tctsung/free-lunch-ai.git` is set before push code
