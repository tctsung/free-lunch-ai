# Default menu presets for zero-config usage: Menu() with no YAML
# Models are ordered by fallback priority (first = preferred)
# Last updated: 2026-03-31
# Sources:
#   Groq free tier:      https://console.groq.com/docs/rate-limits
#   Gemini free tier:    https://ai.google.dev/pricing
#   OpenRouter free:     https://openrouter.ai/models?max_price=0

DEFAULT_MENU = {
    # FAST: Pure speed. Best for summaries, extraction, high-volume tasks.
    "fast": {
        "type": "langchain",
        "timeout": 30,
        "global_timeout": 180,
        "models": [
            {"id": "google::gemini-3-flash-preview"},
            {"id": "google::gemini-2.5-flash"},
            {"id": "google::gemini-2.5-flash-lite"},
            {"id": "groq::llama-3.1-8b-instant"},
            {"id": "groq::openai/gpt-oss-20b"},
            {"id": "openrouter::qwen/qwen3-4b:free"},
        ],
    },

    # THINK: Deep reasoning and complex problem solving.
    "think": {
        "type": "langchain",
        "timeout": 90,
        "global_timeout": 300,
        "models": [
            {"id": "google::gemini-3-pro-preview"},
            {"id": "google::gemini-2.5-pro"},
            {"id": "groq::openai/gpt-oss-120b", "params": {"reasoning_effort": "high"}},
            {"id": "groq::qwen/qwen3-32b"},
            {"id": "openrouter::deepseek/deepseek-r1-0528:free"},
            {"id": "openrouter::nvidia/nemotron-3-super:free"},
        ],
    },

    # AGENT: Models with built-in tools (web search, code execution).
    # Note: Groq Compound models have provider-native tools (not just .bind_tools()).
    "agent": {
        "type": "langchain",
        "timeout": 60,
        "global_timeout": 300,
        "models": [
            {"id": "groq::groq/compound"},
            {"id": "groq::groq/compound-mini"},
            {"id": "groq::openai/gpt-oss-120b"},
        ],
    },
}
