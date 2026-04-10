# Free-Lunch AI 🍱

A plug-and-play router for free LLM APIs. **One YAML, one entrypoint, multiple providers**.

When a model rate-limits or times out, the router quietly switches to the next, helping you max out those free credits and keep your agent moving.

Turns out free lunch exists… if you rotate providers.

---

#### Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start (Zero-Config)](#quick-start-zero-config)
- [Custom Menu (YAML)](#custom-menu-yaml)
  - [1. Configure Keys](#1-configure-keys)
  - [2. Define Menu](#2-define-menu-menuyaml)
  - [3. Run Code](#3-run-code)
- [Built-in Presets](#built-in-presets)

---
### Key Features

* **⚡ Unified Free-Tier Interface**

  Access Groq, Gemini, OpenRouter, and Ollama through a single, consistent API. Just specify `provider::model` in your YAML, and you're ready to go.

* **🚀 Zero-Config Defaults**

  Start immediately with built-in presets (`fast`, `think`, `agent`) — no YAML file needed. See [defaults.py](./src/free_lunch/defaults.py) for the full model list.

* **📄 Infrastructure as Code**

  Manage models, routing priorities, and inference parameters in a single YAML file. No python edits required.

* **🦜 Two Router Modes**

  **LangChain** (`type: langchain`) — full ecosystem support with `.invoke()`, `.bind_tools()`, and agents. **Light** (`type: light`) — zero LangChain dependency, raw httpx, returns plain dicts.

* **🔄 Smart Fallback**

  Per-model and global timeouts, exponential backoff, and automatic removal of permanently failed models (bad auth, invalid model) from the rotation.

---

### Installation

```bash
# Light only (no LangChain dependency, uses raw httpx)
pip install git+https://github.com/tctsung/free-lunch-ai.git

# With LangChain support (.bind_tools(), agents, chains)
pip install "free-lunch-ai[langchain] @ git+https://github.com/tctsung/free-lunch-ai.git"
```

---

### Quick Start (Zero-Config)

No YAML needed. Just set your API keys and go.

```bash
# Set at least one API key
export GROQ_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"
export OLLAMA_API_KEY="your-key"
```

```python
from free_lunch import Menu

menu = Menu()  # auto-detects langchain vs light; override with Menu(router_type="light")

# LangChain installed → returns AIMessage
response = menu.fast().invoke("Explain no free lunch theorem in one sentence.")
print(response.content)
print(response.response_metadata["model_id"])

# Light only → returns dict
result = menu.fast().invoke("Explain no free lunch theorem in one sentence.")
print(result["text"])
print(result["model_id"])
```

Three presets available: `menu.fast()`, `menu.think()`, `menu.agent()`.

---

### Custom Menu (YAML)

For full control, define your own profiles in a YAML file.

#### 1. Configure Keys

Use a `.env` file with the API keys below. The program will load them automatically, or you can export them in your system environment using the same variable names.

- See the example env file here: [`/examples/.env.example`](./examples/.env.example)

| Provider | API Key Name | Get Keys Here |
| :--- | :--- | :--- |
| **Default** | *(none)* | No key required |
| **Groq** | `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| **Google Gemini** | `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/api-keys) |
| **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter Settings](https://openrouter.ai/settings/keys) |
| **Ollama** | `OLLAMA_API_KEY` | [Ollama Settings](https://ollama.com/settings/keys) |

#### 2. Define Menu (`menu.yaml`)

A menu entry describes a capability (e.g., `fast`, `story_teller`) in a YAML file. List models in fallback order. Set `type` to `langchain` or `light`.

```yaml
# LangChain router — works with agents, .bind_tools(), chains
fast:
  type: langchain
  timeout: 30
  global_timeout: 180
  models:
    - id: default::openai           # no API key required
    - id: google::gemini-2.5-flash
    - id: groq::llama-3.1-8b-instant
    - id: openrouter::qwen/qwen3-4b:free

# Light router — no LangChain, returns plain dict
story_teller:
  type: light
  timeout: 90
  global_timeout: 300
  models:
    - id: default::openai-fast      # no API key required
    - id: ollama::deepseek-v3.2:cloud
    - id: groq::openai/gpt-oss-120b
      params:
        reasoning_effort: high
    - id: openrouter::deepseek/deepseek-r1-0528:free
```

#### 3. Run Code

```python
from free_lunch import Menu

my_menu = Menu(yaml_path="menu.yaml")

# LangChain router
response = my_menu.fast().invoke("Explain no free lunch theorem in one sentence.")
print(response.content)

# Light router
result = my_menu.story_teller().invoke("Write a fable about a fox who learns to share.")
print(result["text"])
```

---

### Built-in Presets

When you call `Menu()` with no YAML, these presets are available. See [`defaults.py`](./src/free_lunch/defaults.py) for the full model list.

| Preset | Use Case | Timeout | Models |
| :--- | :--- | :--- | :--- |
| `fast` | Speed, summaries, extraction | 30s / 180s | Gemini Flash, GPT-OSS 20B, Llama 4 Scout, Qwen3 4B |
| `think` | Reasoning, complex problems | 90s / 300s | GPT-OSS 120B, Qwen3 32B, DeepSeek V3.2, Qwen3.5 122B, DeepSeek R1 |
| `agent` | Built-in tools (web search, code exec) | 60s / 300s | Groq Compound, GPT-OSS 120B, Nemotron 3 Super, Kimi K2.5 |

> **Note:** `agent` preset uses Groq Compound models which have provider-native built-in tools (web search, code execution, browser automation) — these are not the same as LangChain's `.bind_tools()`.

> 📋 **Full model list:** See [`doc/models.md`](./doc/models.md) for all available free-tier models across Groq, Gemini, OpenRouter, and Ollama Cloud with rate limits and use-case recommendations.

---

#### TODO
**Short-term**

- Arena mode — batch run same input across all providers, compare outputs
- Batch mode — greedy parallel runs across all providers until all queries answered or all blocked
- CRON job — weekly model/provider health check (automated backup verification)
- Web search tool via DuckDuckGo
- Randomized model smoke tests
- Summary stats ($ saved, free API calls per day)
- Easy tool use & system prompt integration
- Publish to PyPI

**Backlog — New Providers**

All OpenAI-compatible, free tier, worth adding:

| Provider | Free Tier | Why |
| :--- | :--- | :--- |
| Cerebras | 14,400 RPD, 30 RPM | Fastest inference, GPT-OSS 120B + Llama 3.1 8B |
| Mistral | 1M TPM, 1B tokens/month | Very generous, Codestral + proprietary models |
| NVIDIA NIM | 40 RPM | Large model catalog, phone verification required |
| Cohere | 1,000 req/month | Unique models (Command A, Aya multilingual) |
| GitHub Models | Copilot tier dependent | GPT-5, o3, o4-mini if you have Copilot |
| Cloudflare Workers AI | 10,000 neurons/day | Edge inference, many small models |

**Wishlist**

1. Multimodal/audio input
2. Streaming support
3. Async `.ainvoke()` for both routers
