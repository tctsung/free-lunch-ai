# Tests

```bash
# Put keys in examples/.env or .env first
python tests/test_connections.py
python -m unittest tests/test_web_tools.py
python -m unittest tests/test_content_blocks.py
```

`test_connections.py` is a live provider smoke test. `test_web_tools.py` and `test_content_blocks.py` are mocked unit tests and do not need API keys. The LangChain tool assertion is skipped when the `langchain` extra is not installed.
