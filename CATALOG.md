# free-lunch-ai — Function Catalog

Compact reference for AI/LLM coders. Every public function, one line each.
Install: `pip install "free-lunch-ai[all]"`. All imports are `from free_lunch import ...`.

---

## LLM entry point

Build one model client from a `"provider::model"` id. This is the unified entry point.

```python
from free_lunch import LightFactory, LangChainFactory, content_blocks_dict
```

| Function | Signature | Returns | One-liner |
|---|---|---|---|
| `LightFactory.create` | `create(model_id, **kwargs)` | callable model | Single httpx LLM client; `.invoke(messages, timeout=None, **kwargs)` → `{"text","model_id","reasoning"?,"raw_text"?}` |
| `LangChainFactory.create` | `create(model_id, **kwargs)` | `BaseChatModel` | LangChain chat model (supports `.bind_tools()`, `.with_structured_output()`, agents) |
| `content_blocks_dict` | `content_blocks_dict(response, include_raw=True)` | dict | Flatten a LangChain AIMessage/agent response → `{"text","model_id","reasoning"?,"raw_text"?,"raw_response"?}` |

- **model_id format:** `"provider::model"`, e.g. `"groq::llama-3.1-8b-instant"`.
- **`.invoke` messages:** a string, or `[{"role":"user","content":"..."}]`.
- **Light vs LangChain:** Light = raw httpx, plain-dict output. LangChain = full ecosystem compat (tools/agents/structured output).

```python
model = LightFactory.create("groq::llama-3.1-8b-instant")
out = model.invoke("Summarize RAG in one sentence.")   # {"text": ..., "model_id": ...}
```

---

## Built-in tools

Plain functions returning JSON-friendly dicts; usable directly or as agent tools.

```python
from free_lunch import web_search, fetch_url, current_time, read_file, build_langchain_tools
```

| Function | Signature | Returns | One-liner |
|---|---|---|---|
| `web_search` | `web_search(query, max_results=5)` | `list[{title,url,snippet}]` | DuckDuckGo web search |
| `fetch_url` | `fetch_url(url)` | `{url, content}` | Fetch page as Markdown (Jina Reader first → DDGS fallback; handles JS/SPA pages) |
| `current_time` | `current_time(timezone=None)` | `{date, weekday, time, timezone}` | Current date/time, optional IANA timezone |
| `read_file` | `read_file(path)` | `{path, content, format}` | Local file → Markdown: PDF/DOCX/XLSX/HTML converted, all other suffixes read as UTF-8 text |
| `build_langchain_tools` | `build_langchain_tools(*functions)` | `list` of LC tools | Wrap the above (or any callables) as LangChain tools; no args → wraps all four |

---

## RAG

```python
from free_lunch import chunk_documents, VectorStore
```

### `chunk_documents` — text chunker

```python
chunk_documents(sources, chunk_size=512, overlap=64, tokenizer=None, separators="default") -> list[dict]
```

One-liner: split text/files into overlapping chunks → `[{"document","source","chunk_index"}]`.

- **`sources`** — auto-detected per item: glob (`"docs/*.py"`, `"docs/**/*.md"`) → directory (reads all, recursive) → file path (via `read_file`) → else raw text (named `raw_0`, `raw_1`, …). A single string or a mixed list.
- **`chunk_size`/`overlap`** — target chunk length and words carried from the previous chunk, both measured by `tokenizer`.
- **`tokenizer`** — `(str) -> int`; default is word count. Pass `len` for character count.
- **`separators`** — `"default"` (markdown headings → blank lines → sentences), `None`/`[]` (word boundaries only), or a custom regex/string priority cascade.
- Output key is `"document"` (not `"text"`) to match Qdrant payload convention → feed straight into `VectorStore.add`.

### `VectorStore` — Qdrant hybrid vector store

```python
VectorStore(collection="free_lunch", location=":memory:",
            dense_model="BAAI/bge-small-en-v1.5", sparse_model="Qdrant/bm25")
```

Hybrid dense + BM25 sparse search (RRF fusion), local via fastembed/onnxruntime.
Chunks are addressed by their `(source, chunk_index)` coordinate; point ids are a deterministic `uuid5` of that pair, so re-adding updates in place.

**`location` modes:**
- `":memory:"` (default) — in-process, ephemeral. Fastest; for demos / data that fits in RAM.
- `"./qdrant_data"` (a path) — embedded, persisted to local disk. Survives restarts, no server. Slower than memory.
- `"http(s)://…"` — remote/cloud server (reads `QDRANT_API_KEY` from env). The right choice for large corpora: a server can memory-map vectors/payload on disk (`on_disk`), keeping only hot data in RAM so storage exceeds memory.

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `add` | `add(chunks)` | `list[str]` (ids) | Upsert chunk dict(s) (need `source`+`chunk_index`); embeds `document`, stores dict verbatim; idempotent |
| `retrieve` | `retrieve(query, limit=5, source=None)` | `list[dict]` | Hybrid semantic search (dense+BM25 RRF), ranked best-first; optional `source` filter |
| `lookup` | `lookup(source, chunk_index=None)` | `list[dict]` | Exact fetch, no embedding: `None`→all chunks of source (paginated), int→one, list→several |
| `delete` | `delete(ids=None, source=None)` | `None` | Delete by point ids or by `source` filter |

```python
# location=path persists to disk, so you embed once and reuse across runs
# (embedding is the slow step) — re-running just reopens the existing collection.
store = VectorStore(location="./qdrant_data")
store.add(chunk_documents("docs/*.md"))                 # skip on later runs if already indexed
hits = store.retrieve("how do I install?", limit=3)     # [{id,score,document,source,chunk_index,...}]
ctx  = store.lookup(hits[0]["source"],                  # small-to-large: pull neighbors
                    chunk_index=[hits[0]["chunk_index"] + d for d in (-1, 0, 1)])
```

---

## Providers

`provider` in `provider::model`: `groq`, `google`, `openrouter`, `ollama`, `pollinations`.
Each reads its API key from an env var (e.g. `GROQ_API_KEY`); load your `.env` before use.
