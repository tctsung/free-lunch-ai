# Free-Lunch AI 🍱

A plug-and-play router for free LLM APIs. **One YAML, one entrypoint, multiple providers**. LangChain compatible for painless integration.

When a model rate-limits or times out, the router quietly switches to the next, helping you max out those free credits and keep your agent moving.

Turns out free lunch exists… if you rotate providers.

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

  Access Groq, Gemini, and OpenRouter through a single, consistent API. Just specify `provider::model` in your YAML, and you’re ready to go.

* **📄 Infrastructure as Code**

  Manage models, routing priorities, tweak inference parameters in a single YAML file. No python edits required

* **🦜 LangChain Native**

  Works seamlessly with LangChain ecosystem. Supports standard methods like `.invoke()`, `create_agent()`, and `.bind_tools()`, making it a drop-in replacement.

---

### Installation

```bash
pip install git+https://github.com/tctsung/free-lunch-ai.git
```

---

### Quick Start

#### 1. Configure Keys

Use a `.env` file with the API keys below. The program will load them automatically, or you can export them in your system environment using the same variable names.

- See the example env file here: [`/example/.env.example`](./examples/.env.example)

| Provider | API Key Name | Get Keys Here |
| :--- | :--- | :--- |
| **Groq** | `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| **Google Gemini** | `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/api-keys) |
| **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter Settings](https://openrouter.ai/settings/keys) |

#### 2. Define Menu (`menu.yaml`)

A menu entry describes a capability (e.g., `fast`, `story_teller`) in a YAML file. List models in fallback order

```yaml
# Fast-response profile named 'fast'
fast:
  type: langchain
  models:
    - id: google::gemini-2.5-flash
    - id: groq::moonshotai/kimi-k2-instruct-0905
    - id: openrouter::qwen/qwen3-4b:free

# Define another profile
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
my_menu = Menu(yaml_path = "menu.yaml")   #  env_path = ".env"

# 2. Get the router by user defined name
fast_llm = my_menu.fast()  # timeout = 180 (default timeout is 3 min)

# 3. Use it (Standard LangChain syntax)
response = fast_llm.invoke("Explain no free lunch theorem in one sentence.")
print(response.content)
```


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
