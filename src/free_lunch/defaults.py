# Default menu presets for zero-config usage: Menu() with no YAML
# Models are ordered by fallback priority (first = preferred)
# Priority: best quality-per-latency first, highest quota providers preferred
# Note: "type" is set dynamically by Menu() based on installed packages
# Last updated: 2026-03-31
# Sources:
#   Groq free tier:      https://console.groq.com/docs/rate-limits
#   Gemini free tier:    https://ai.google.dev/pricing
#   OpenRouter free:     https://openrouter.ai/models?max_price=0
#   Ollama cloud:        https://ollama.com/search?c=cloud

DEFAULT_MENU = {
    # FAST: Best quality at speed. Summaries, extraction, high-volume tasks.
    "fast": {
        "timeout": 30,
        "global_timeout": 180,
        "models": [
            {"id": "default::openai"},                        # no key needed
            {"id": "default::openai-fast"},                   # no key needed
            {"id": "google::gemini-2.5-flash"},               # 10 RPM, top-tier flash quality
            {"id": "groq::openai/gpt-oss-20b"},               # 30 RPM, fast + good quality
            {"id": "groq::meta-llama/llama-4-scout-17b-16e-instruct"},  # 30K TPM, MoE
            {"id": "ollama::gpt-oss:20b-cloud"},              # full-weight fallback
            {"id": "openrouter::stepfun/step-3.5-flash:free"},  # 256K context
            {"id": "openrouter::qwen/qwen3-4b:free"},         # lightweight fallback
            {"id": "google::gemini-2.5-flash-lite"},          # 15 RPM, last resort
            {"id": "groq::llama-3.1-8b-instant"},             # 14.4K RPD, safety net
        ],
    },

    # THINK: Deep reasoning and complex problem solving.
    "think": {
        "timeout": 90,
        "global_timeout": 300,
        "models": [
            {"id": "groq::openai/gpt-oss-120b", "params": {"reasoning_effort": "high"}},
            {"id": "groq::qwen/qwen3-32b"},                  # 60 RPM, good reasoning on Groq
            {"id": "ollama::deepseek-v3.2:cloud"},            # full-weight, MMLU 94.2%
            {"id": "ollama::qwen3.5:122b-cloud"},             # 122B, top open model
            {"id": "openrouter::qwen/qwen3-next-80b:free"},   # 262K context, beats Qwen3-32B
            {"id": "openrouter::deepseek/deepseek-r1-0528:free"},
            {"id": "openrouter::nvidia/nemotron-3-super:free"},
            {"id": "google::gemini-2.5-pro"},                 # 5 RPM, 100 RPD — last resort
        ],
    },

    # AGENT: Models with built-in tools (web search, code execution).
    # Note: Groq Compound models have provider-native tools (not just .bind_tools()).
    "agent": {
        "timeout": 60,
        "global_timeout": 300,
        "models": [
            {"id": "groq::groq/compound"},                    # built-in web search, code exec
            {"id": "groq::groq/compound-mini"},               # lighter compound
            {"id": "groq::openai/gpt-oss-120b"},              # tool use via .bind_tools()
            {"id": "ollama::nemotron-3-super:120b-cloud"},    # 120B MoE, tool calling
            {"id": "ollama::kimi-k2.5:cloud"},                # multimodal, agentic
            {"id": "openrouter::nvidia/nemotron-3-super:free"},
            {"id": "openrouter::openai/gpt-oss-120b:free"},   # cross-provider fallback
        ],
    },
}
