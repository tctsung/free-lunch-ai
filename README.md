# Free-Lunch AI 🍱

A plug-and-play router for free LLM APIs. **One YAML, one entrypoint, multiple providers**. LangChain compatible for painless integration.

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

  Access Groq, Gemini, and OpenRouter through a single, consistent API. Just specify `provider::model` in your YAML, and you're ready to go.

* **🚀 Zero-Config Defaults**

  Start immediately with built-in presets (`fast`, `think`, `agent`) — no YAML file needed. See [defaults.py](./src/free_lunch/defaults.py) for the full model list.

* **📄 Infrastructure as Code**

  Manage models, routing priorities, and inference parameters in a single YAML file. No python edits required.

* **🦜 LangChain Native**

  Works seamlessly with LangChain ecosystem. Supports standard methods like `.invoke()`, `create_agent()`, and `.bind_tools()`, making it a drop-in replacement.

* **🔄 Smart Fallback**

  Per-model and global timeouts, exponential backoff, and automatic removal of permanently failed models (bad auth, invalid model) from the rotation.

---

### Installation

```bash
pip install git+https://github.com/tctsung/free-lunch-ai.git
```

---

### Quick Start (Zero-Config)

No YAML needed. Just set your API keys and go.

```bash
# Set at least one API key
export GROQ_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"
```

```python
from free_lunch import Menu

menu = Menu()  # uses built-in presets

# Fast: speed-optimized, best for summaries & simple tasks
fast_llm = menu.fast()
response = fast_llm.invoke("Explain no free lunch theorem in one sentence.")
print(response.content)

# Think: reasoning-optimized, best for complex problems
think_llm = menu.think()
response = think_llm.invoke("Prove that the square root of 2 is irrational.")
print(response.content)

# Agent: models with built-in tools (web search, code execution)
agent_llm = menu.agent()
response = agent_llm.invoke("What is the weather in NYC right now?")
print(response.content)
```

---

### Custom Menu (YAML)

For full control, define your own profiles in a YAML file.

#### 1. Configure Keys

Use a `.env` file with the API keys below. The program will load them automatically, or you can export them in your system environment using the same variable names.

- See the example env file here: [`/examples/.env.example`](./examples/.env.example)

| Provider | API Key Name | Get Keys Here |
| :--- | :--- | :--- |
| **Groq** | `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| **Google Gemini** | `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/api-keys) |
| **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter Settings](https://openrouter.ai/settings/keys) |

#### 2. Define Menu (`menu.yaml`)

A menu entry describes a capability (e.g., `fast`, `story_teller`) in a YAML file. List models in fallback order. Use `timeout` (per-model, seconds) and `global_timeout` (total retry budget) to control timing.

```yaml
# Fast-response profile
fast:
  type: langchain
  timeout: 30           # per-model request timeout (default: 30s)
  global_timeout: 180   # total retry budget (default: 180s)
  models:
    - id: google::gemini-2.5-flash
    - id: groq::llama-3.1-8b-instant
    - id: openrouter::qwen/qwen3-4b:free

# Deep reasoning profile
story_teller:
  type: langchain
  timeout: 90
  global_timeout: 300
  models:
    - id: google::gemini-2.5-pro
    - id: groq::openai/gpt-oss-120b
      params:
        reasoning_effort: high
    - id: openrouter::deepseek/deepseek-r1-0528:free
```

#### 3. Run Code

```python
from free_lunch import Menu

# Initialize with your YAML (automatically loads .env)
my_menu = Menu(yaml_path="menu.yaml")   #  env_path=".env"

# Get the router by profile name
fast_llm = my_menu.fast()

# Use it — standard LangChain syntax
response = fast_llm.invoke("Explain no free lunch theorem in one sentence.")
print(response.content)
```

---

### Built-in Presets

When you call `Menu()` with no YAML, these presets are available. See [`defaults.py`](./src/free_lunch/defaults.py) for the full model list.

| Preset | Use Case | Timeout | Models |
| :--- | :--- | :--- | :--- |
| `fast` | Speed, summaries, extraction | 30s / 180s | Gemini Flash, Llama 3.1 8B, GPT-OSS 20B, Qwen3 4B |
| `think` | Reasoning, complex problems | 90s / 300s | Gemini 2.5 Pro, GPT-OSS 120B, Qwen3 32B, DeepSeek R1, Nemotron 3 |
| `agent` | Built-in tools (web search, code exec) | 60s / 300s | Groq Compound, Compound Mini, GPT-OSS 120B |

> **Note:** `agent` preset uses Groq Compound models which have provider-native built-in tools (web search, code execution, browser automation) — these are not the same as LangChain's `.bind_tools()`.

> 📋 **Full model list:** See [`doc/models.md`](./doc/models.md) for all available free-tier models across Groq, Gemini, and OpenRouter with rate limits and use-case recommendations.

---

#### TODO
**short-term**

- Add sample in ipynb, colab (tutorial), .py (react usecase)
- summary stats supporting free lunch package benefit (eg. $ saved, no. of free api calls per day)
- add skill import with local `.md` file
- easy integrate tool use, system prompt

**Wishlist**

1. multimodal/audio input
2. light weight version
