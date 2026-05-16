# Default menu presets for zero-config usage: Menu() with no YAML
# Models are ordered by fallback priority (first = preferred)
# Priority: best quality-per-latency first, highest quota providers preferred
# Note: "type" is set dynamically by Menu() based on installed packages
# Last updated: 2026-05-16
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
            {"id": "groq::openai/gpt-oss-20b"},               # 30 RPM, fast + good quality
            {"id": "google::gemini-2.5-flash"},               # 10 RPM, top-tier flash quality
            {"id": "groq::meta-llama/llama-4-scout-17b-16e-instruct"},  # 30K TPM, MoE
            {"id": "ollama::gpt-oss:20b-cloud"},              # full-weight fallback
            {"id": "openrouter::liquid/lfm-2.5-1.2b-instruct:free"},  # lightweight fallback
            {"id": "openrouter::google/gemma-4-31b-it:free"},  # higher-quality free OR fallback
            {"id": "openrouter::google/gemma-4-26b-a4b-it:free"},  # efficient Gemma 4 MoE fallback
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
            {"id": "ollama::gpt-oss:120b-cloud"},             # full-weight fallback
            {"id": "ollama::nemotron-3-super:cloud"},         # strong long-context reasoner
            {"id": "openrouter::google/gemma-4-31b-it:free"},  # current high-quality free OR model
            {"id": "openrouter::google/gemma-4-26b-a4b-it:free"},  # current efficient Gemma 4 MoE
            {"id": "openrouter::nvidia/nemotron-3-super-120b-a12b:free"},
            {"id": "openrouter::openai/gpt-oss-120b:free"},
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
            {"id": "ollama::nemotron-3-super:cloud"},         # 120B MoE, tool calling
            {"id": "ollama::gpt-oss:120b-cloud"},             # strong tool use on Ollama cloud
            {"id": "openrouter::nvidia/nemotron-3-super-120b-a12b:free"},
            {"id": "openrouter::google/gemma-4-31b-it:free"},  # native function calling
            {"id": "openrouter::google/gemma-4-26b-a4b-it:free"},  # native function calling, lighter
            {"id": "openrouter::openai/gpt-oss-120b:free"},   # cross-provider fallback
        ],
    },
}
