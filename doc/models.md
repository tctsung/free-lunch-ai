# Free-Tier Model Reference

All models below are available on free tiers as of March 2026. Use the `provider::model` format in your YAML or defaults.

> **Tip:** This list changes frequently. Check provider pages for the latest:
> [Groq Rate Limits](https://console.groq.com/docs/rate-limits) ·
> [Gemini Pricing](https://ai.google.dev/pricing) ·
> [OpenRouter Free Models](https://openrouter.ai/models?max_price=0)

---

## Groq

All models below are free with rate limits (no credit card required).

| Model ID | RPM | RPD | TPM | Best For |
| :--- | :--- | :--- | :--- | :--- |
| `groq::llama-3.1-8b-instant` | 30 | 14,400 | 6K | Fast, lightweight tasks |
| `groq::llama-3.3-70b-versatile` | 30 | 1,000 | 12K | General purpose |
| `groq::meta-llama/llama-4-scout-17b-16e-instruct` | 30 | 1,000 | 30K | General, MoE |
| `groq::moonshotai/kimi-k2-instruct-0905` | 60 | 1,000 | 10K | General, prompt caching |
| `groq::openai/gpt-oss-20b` | 30 | 1,000 | 8K | Fast, edge deployment |
| `groq::openai/gpt-oss-120b` | 30 | 1,000 | 8K | General, tool use |
| `groq::qwen/qwen3-32b` | 60 | 1,000 | 6K | Reasoning, multilingual |
| `groq::groq/compound` | 30 | 250 | 70K | Agentic (built-in web search, code exec) |
| `groq::groq/compound-mini` | 30 | 250 | 70K | Agentic (lighter, faster) |

**Notes:**
- Compound models have provider-native built-in tools (web search, code execution, browser automation).
- `gpt-oss-safeguard-20b` and `llama-prompt-guard-*` are moderation/guardrail models, not general chat.

---

## Google Gemini

All models below are free via Google AI Studio (no credit card required).

| Model ID | RPM | RPD | Best For |
| :--- | :--- | :--- | :--- |
| `google::gemini-3-pro-preview` | ~5 | ~100 | Reasoning, complex tasks (preview) |
| `google::gemini-3-flash-preview` | ~10 | ~250 | Fast, general purpose (preview) |
| `google::gemini-2.5-pro` | 5 | 100 | Reasoning, complex tasks |
| `google::gemini-2.5-flash` | 10 | 250 | Fast, general purpose |
| `google::gemini-2.5-flash-lite` | 15 | 1,000 | Highest free throughput |

**Notes:**
- Gemini 3 models are in preview and may change or be deprecated.
- Gemini 2.5 Pro has the lowest free-tier limits (5 RPM, 100 RPD) — best as a fallback, not primary.

---

## OpenRouter

Append `:free` to model IDs. No credit card required.

| Model ID | Context | Best For |
| :--- | :--- | :--- |
| `openrouter::nvidia/nemotron-3-super:free` | 262K | Agents, long context |
| `openrouter::qwen/qwen3-next-80b:free` | 262K | RAG, agents |
| `openrouter::mistralai/devstral-2512:free` | 262K | Coding |
| `openrouter::qwen/qwen3-coder:free` | 262K | Coding |
| `openrouter::xiaomi/mimo-v2-flash:free` | 262K | Coding |
| `openrouter::nvidia/nemotron-3-nano:free` | 256K | Agents (lighter) |
| `openrouter::stepfun/step-3.5-flash:free` | 256K | General |
| `openrouter::minimax/minimax-m2.5:free` | 197K | Productivity (Office docs) |
| `openrouter::deepseek/deepseek-r1-0528:free` | 164K | Reasoning |
| `openrouter::nousresearch/hermes-3-llama-3.1-405b:free` | 131K | General |
| `openrouter::meta-llama/llama-3.3-70b-instruct:free` | 65K | General |
| `openrouter::openai/gpt-oss-120b:free` | 131K | General, tool use |
| `openrouter::openai/gpt-oss-20b:free` | 131K | Edge, self-host |
| `openrouter::zhipu-ai/glm-4.5-air:free` | 131K | Multilingual |
| `openrouter::google/gemma-3-27b-it:free` | 131K | Multimodal, multilingual |
| `openrouter::arcee-ai/arcee-trinity-large:free` | 131K | Reasoning |
| `openrouter::arcee-ai/arcee-trinity-mini:free` | 131K | Fast |
| `openrouter::meta-llama/llama-3.2-3b-instruct:free` | 131K | Edge, fast |
| `openrouter::nvidia/nemotron-nano-12b-v2-vl:free` | 128K | Multimodal (video, docs) |
| `openrouter::nvidia/nemotron-nano-9b-v2:free` | 128K | Reasoning |
| `openrouter::mistralai/mistral-small-3.1-24b-instruct:free` | 128K | General |
| `openrouter::qwen/qwen3-4b:free` | 41K | Edge, fast |
| `openrouter::cognitivecomputations/dolphin-mistral-24b:free` | 33K | Uncensored |
| `openrouter::google/gemma-3-12b-it:free` | 33K | Multimodal |
| `openrouter::google/gemma-3-4b-it:free` | 33K | Edge, fast |
| `openrouter::liquid/lfm2-5-1.2b-thinking:free` | 33K | Reasoning (tiny) |
| `openrouter::liquid/lfm2-5-1.2b-instruct:free` | 33K | Chat (tiny) |
| `openrouter::google/gemma-3n-e4b-it:free` | 8K | Mobile |
| `openrouter::google/gemma-3n-e2b-it:free` | 8K | Mobile |

**Notes:**
- Free tier has lower rate limits and queue priority than paid.
- Models can be rotated out of the free tier at any time.

---

## Ollama Cloud

Cloud models run on Ollama's infrastructure via an OpenAI-compatible API. Free tier includes light usage with session limits that reset every 5 hours and weekly limits that reset every 7 days. API key required from [Ollama Settings](https://ollama.com/settings/keys).

| Model ID | Params | Best For |
| :--- | :--- | :--- |
| `ollama::qwen3.5:122b-cloud` | 122B | General, reasoning, multimodal |
| `ollama::qwen3-coder-next:cloud` | — | Coding, agentic workflows |
| `ollama::qwen3-next:80b-cloud` | 80B | Reasoning, agents |
| `ollama::minimax-m2.7:cloud` | — | Coding, agentic, productivity |
| `ollama::minimax-m2.5:cloud` | — | Productivity, coding |
| `ollama::kimi-k2.5:cloud` | — | Multimodal, agentic |
| `ollama::nemotron-3-super:120b-cloud` | 120B (12B active) | Agents, MoE efficiency |
| `ollama::nemotron-3-nano:30b-cloud` | 30B | Agents (lighter) |
| `ollama::devstral-2:123b-cloud` | 123B | Coding, multi-file edits |
| `ollama::devstral-small-2:24b-cloud` | 24B | Coding (lighter) |
| `ollama::deepseek-v3.2:cloud` | — | Reasoning, agents |
| `ollama::glm-5:cloud` | 744B (40B active) | Reasoning, systems engineering |
| `ollama::cogito-2.1:671b-cloud` | 671B | General (MIT license) |
| `ollama::gpt-oss:120b-cloud` | 120B | General, tool use |
| `ollama::gpt-oss:20b-cloud` | 20B | Fast, edge deployment |

**Notes:**
- Free plan allows 1 concurrent cloud model. Session limits reset every 5 hours.
- Uses OpenAI-compatible API (`https://ollama.com/v1/`) — no extra Python dependency needed.
- Cloud models use native weights (no quantization) on datacenter GPUs.
- Tool calling works via the OpenAI-compatible endpoint for supported models.
