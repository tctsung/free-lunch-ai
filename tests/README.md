# Tests

```bash
# Put keys in examples/.env or .env first
python tests/test_connections.py
```

Tests one current small/fast model per configured provider across both Light and LangChain routers, then runs a multi-provider fallback smoke test. Skips providers without API keys.
