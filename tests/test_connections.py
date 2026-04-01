"""
Connection test for all providers × both router types.
Run: python tests/test_connections.py
Skips providers whose API keys are not set.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(override=True)

from free_lunch import Menu, content_blocks_dict
from free_lunch.light_router import LightRouter

PROMPT = "Say 'hello' and nothing else."

# One small/fast model per provider
TEST_MODELS = [
    ("groq",       "GROQ_API_KEY",       {"id": "groq::llama-3.1-8b-instant"}),
    ("google",     "GOOGLE_API_KEY",      {"id": "google::gemini-2.5-flash-lite"}),
    ("openrouter", "OPENROUTER_API_KEY",  {"id": "openrouter::qwen/qwen3-4b:free"}),
    ("ollama",     "OLLAMA_API_KEY",      {"id": "ollama::gpt-oss:20b-cloud"}),
]


def get_available():
    available = []
    for provider, env_key, model in TEST_MODELS:
        if os.environ.get(env_key):
            available.append((provider, model))
        else:
            print(f"  SKIP  {provider:12s} — {env_key} not set")
    return available


def run_test(name, invoke_fn):
    """Run a single test, print result."""
    try:
        start = time.time()
        result = invoke_fn()
        elapsed = time.time() - start
        text = result.get("text", "") if isinstance(result, dict) else result.content
        model = result.get("model_id", "") if isinstance(result, dict) else result.response_metadata.get("model_id", "")
        assert text, "Empty response"
        print(f"  OK    {name:40s} ({elapsed:.1f}s) {model}")
        return True
    except Exception as e:
        print(f"  FAIL  {name:40s} → {e}")
        return False


if __name__ == "__main__":
    print("Free-Lunch AI — Connection Tests\n")
    models = get_available()
    if not models:
        print("No API keys found."); sys.exit(1)

    ok = True

    # Per-provider tests
    for provider, model in models:
        # Light
        r = LightRouter(func_name="test", models=[model], timeout=30, global_timeout=30)
        ok &= run_test(f"light  | {provider}", lambda r=r: r.invoke(PROMPT))

        # LangChain
        m = Menu(); m.yaml_content = {"t": {"type": "langchain", "timeout": 30, "global_timeout": 30, "models": [model]}}
        try:
            ok &= run_test(f"lc     | {provider}", lambda m=m: m.t().invoke(PROMPT))
        except ImportError:
            print(f"  SKIP  lc     | {provider:12s} — langchain not installed")

    # Fallback test (all providers in one router)
    all_models = [m for _, m in models]
    r = LightRouter(func_name="fallback", models=all_models, timeout=30, global_timeout=60)
    ok &= run_test("light  | fallback (all)", lambda: r.invoke(PROMPT))

    print(f"\n{'All passed ✓' if ok else 'Some failed ✗'}")
    sys.exit(0 if ok else 1)
