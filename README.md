# Free-Lunch AI 🍱

**A plug-and-play router for free LLM APIs.** Define models in YAML, explore ideas instantly, and never hard-code a provider again. Perfect for building agents on a budget.

---

#### Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [1. Configure Keys](#1-configure-keys)
  - [2. Define Menu](#2-define-menu-menuyaml)
  - [3. Run Code](#3-run-code-python)
---
### Key Features

* **⚡ Unified Free-Tier Interface**
  Access Groq, Gemini, and OpenRouter through a single, consistent API. Stop managing disparate import paths and client libraries—just use `provider::model` and you're good to go.

* **📄 Infrastructure as Code**
  Define model configurations and routing priorities in a simple YAML file. Switch providers, adjust temperatures, or update failover logic without touching a single line of Python code.

* **🔄 Automatic Failover**
  Built for resilience. If a free-tier API hits a rate limit or times out, the router automatically rotates to the next available model in your list, ensuring your agent never gets stuck.

* **🦜 LangChain Native**
  Fully compatible with the LangChain ecosystem. Supports standard methods like `.invoke()`, `.stream()`, and `.bind_tools()`, making it a drop-in replacement for `ChatOpenAI`.

---

### Installation

```bash
pip install git+https://github.com/tctsung/free-lunch-ai.git
```

---

### Quick Start

#### 1. Configure Keys

Create a `.env` file with your free API keys. The program will automatically load them from here or your system environment.

| Provider | API Key Name | Get Keys Here |
| :--- | :--- | :--- |
| **Groq** | `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| **Google Gemini** | `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/api-keys) |
| **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter Settings](https://openrouter.ai/settings/keys) |

**Example `.env` file:**

```bash
GOOGLE_API_KEY=AIxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxx
```

#### 2. Define Menu (`menu.yaml`)

Define your agent's "capabilities" (e.g., `fast_helper`, `story_teller`) in a YAML file. List models in order of priority.

```yaml
# Define a capability named 'fast'
fast:
  type: langchain
  models:
    - id: google::gemini-2.5-flash
    - id: groq::moonshotai/kimi-k2-instruct-0905
    - id: openrouter::qwen/qwen3-4b:free

# Define another capability
story_teller:
  type: langchain
  models:
    - id: google::gemini-2.5-pro
    - id: groq::openai/gpt-oss-120b
      params:
        reasoning_effort: high
    - id: openrouter::tngtech/deepseek-r1t2-chimera:free
```

#### 3. Run Code (`python`)

Load your menu and start using the router. It behaves exactly like a standard LangChain chat model.

```python
from free_lunch import Menu

# 1. Initialize the menu (automatically loads .env)
my_menu = Menu("menu.yaml")

# 2. Get the router by name
# This creates a unified model that handles failover automatically
fast_llm = my_menu.fast()

# 3. Use it (Standard LangChain syntax)
response = fast_llm.invoke("Explain quantum computing in one sentence.")
print(response.content)
```


---
#### TODO
**short-term**

- Add simple example in readme & ipynb
- Add py file agent workflow example
- streamlit example
- add skill import with local `.md` file
- easy integrate tool use

**Wishlist**

1. multimodal/audio input
2. light weight version
