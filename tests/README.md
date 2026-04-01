# Tests

```bash
# Set API keys first (or use .env file)
python tests/test_connections.py
```

Tests each provider (Groq, Gemini, OpenRouter, Ollama) with both Light and LangChain routers. Skips providers without API keys.
