"""RAG preprocessing helpers (stdlib only).

`chunk_documents` turns files, directories, or raw strings into overlapping
text chunks ready for embedding/indexing. Zero external deps.
"""

from __future__ import annotations

import glob
import logging
import os
import re
import uuid
from typing import Callable

logger = logging.getLogger(__name__)

# Default split cascade: markdown heading lines, blank lines, sentence ends.
_DEFAULT_SEPARATORS = [r"^#{1,6}\s+.+$", "\n\n", ". "]


def chunk_documents(
    sources: list[str] | str,
    chunk_size: int = 512,
    overlap: int = 64,
    tokenizer: Callable[[str], int] | None = None,
    separators: list[str] | None = "default",
) -> list[dict]:
    """Split documents into overlapping text chunks.

    sources: a single string or a list of strings. Each string is auto-detected,
        in this priority order:

        1. **Glob pattern** — contains ``*``, ``?``, or ``[``. Selects files by
           extension/name. ``"docs/*.py"`` matches that one directory;
           ``"docs/**/*.md"`` recurses into subdirectories (use ``**`` for
           nesting — a plain ``*`` does not recurse).
        2. **Directory** — an existing folder. Reads *every* file in it,
           recursively. (No extension filter — use a glob for that.)
        3. **File path** — an existing file. Read via ``read_file`` so PDF /
           DOCX / XLSX / HTML become Markdown; other suffixes are read as text.
        4. **Raw text** — anything else. Chunked directly and named ``raw_0``,
           ``raw_1``, ... in order.

        Lists may mix all four, e.g. ``["notes.md", "src/*.py", "raw text"]``.
        ``source`` in each output dict is the file path (1–3) or ``raw_N`` (4).
    chunk_size: target max length per chunk, measured by ``tokenizer``.
    overlap: words from the end of the previous chunk prepended to the next.
    tokenizer: ``(str) -> int`` length measure. Defaults to word count.
    separators: ``"default"`` (headings, blank lines, sentences), ``None``/``[]``
        (word boundaries only), or a custom priority cascade.

    Returns a list of ``{"document", "source", "chunk_index"}`` dicts. The text
    field is named ``"document"`` (not ``"text"``) to match Qdrant's payload
    convention — qdrant-client stores chunk text under a ``"document"`` key and
    ``QueryResponse.document`` reads it back — so ``VectorStore.add`` can store a
    chunk dict verbatim with no key remapping.
    """
    measure = tokenizer if callable(tokenizer) else (lambda t: len(t.split()))

    if separators == "default":
        seps = _DEFAULT_SEPARATORS
    elif not separators:  # None or []
        seps = []
    else:
        seps = list(separators)
    sep_specs = [(s, _is_regex(s)) for s in seps]

    out: list[dict] = []
    for name, text in _gather(sources):
        pieces = _split_recursive(text, sep_specs, chunk_size, measure)
        cores = _merge(pieces, chunk_size, measure)

        prev_core: str | None = None
        idx = 0
        for core in cores:
            if not core.strip():
                continue
            if overlap and prev_core:
                ov = prev_core.split()[-overlap:]
                ctext = (" ".join(ov) + " " + core).strip()
            else:
                ctext = core.strip()
            if not ctext:
                continue

            # "document": matches Qdrant payload / QueryResponse.document key
            out.append({"document": ctext, "source": name, "chunk_index": idx})
            idx += 1
            prev_core = core
    return out


# --- source gathering -------------------------------------------------------


def _gather(sources: list[str] | str) -> list[tuple[str, str]]:
    if isinstance(sources, str):
        sources = [sources]
    docs: list[tuple[str, str]] = []
    raw_i = 0
    for item in sources:
        if _is_glob(item):
            matches = sorted(p for p in glob.glob(item, recursive=True) if _is_file(p))
            logger.info("glob pattern %r detected: %d files identified", item, len(matches))
            for f in matches:
                docs.append((f, _read(f)))
        elif _is_dir(item):
            for f in sorted(_walk_files(item)):
                docs.append((f, _read(f)))
        elif _is_file(item):
            docs.append((item, _read(item)))
        else:
            docs.append((f"raw_{raw_i}", item))
            raw_i += 1
    return docs


def _is_glob(s) -> bool:
    return isinstance(s, str) and any(c in s for c in "*?[")


def _is_file(s) -> bool:
    try:
        return isinstance(s, str) and os.path.isfile(s)
    except (OSError, ValueError):
        return False


def _is_dir(s) -> bool:
    try:
        return isinstance(s, str) and os.path.isdir(s)
    except (OSError, ValueError):
        return False


def _walk_files(root: str) -> list[str]:
    found: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            found.append(os.path.join(dirpath, fn))
    return found


def _read(path: str) -> str:
    """Read a file to text via ``tools.read_file`` (PDF/DOCX/XLSX/HTML →
    Markdown, everything else → UTF-8 text). Lazy import keeps rag import-light
    and avoids a cycle with tools."""
    from .tools import read_file

    return read_file(path)["content"]


# --- separator handling -----------------------------------------------------


def _is_regex(s: str) -> bool:
    return (
        s.startswith("^")
        or r"\s+" in s
        or any(c in s for c in ("+", "*", "(", ")"))
    )


def _apply_sep(text: str, sep: str, is_rx: bool) -> list[str]:
    """Split text on a separator, keeping the separator attached so the
    pieces concatenate back to the original. Regex matches lead the next
    segment (headings start a block); literals trail the previous one."""
    if is_rx:
        starts = [m.start() for m in re.compile(sep, re.MULTILINE).finditer(text)]
        if not starts:
            return [text]
        bounds = starts + [len(text)]
        segments: list[str] = []
        if starts[0] > 0:
            segments.append(text[: starts[0]])
        for i in range(len(starts)):
            seg = text[starts[i] : bounds[i + 1]]
            if seg:
                segments.append(seg)
        return segments
    if sep not in text:
        return [text]
    pieces = text.split(sep)
    segments = [
        (p + sep if j < len(pieces) - 1 else p) for j, p in enumerate(pieces)
    ]
    return [s for s in segments if s != ""]


def _split_words(text: str, chunk_size: int, measure) -> list[str]:
    # Keep trailing whitespace on each token so chunks preserve line structure.
    words = re.findall(r"\S+\s*", text)
    if not words:
        return []
    chunks: list[str] = []
    cur = ""
    for w in words:
        if cur and measure(cur + w) > chunk_size:
            chunks.append(cur)
            cur = w
        else:
            cur += w
    if cur:
        chunks.append(cur)
    return chunks


def _split_recursive(text, sep_specs, chunk_size, measure) -> list[str]:
    if not text.strip():
        return []
    if measure(text) <= chunk_size:
        return [text]
    if not sep_specs:
        return _split_words(text, chunk_size, measure)

    sep, is_rx = sep_specs[0]
    rest = sep_specs[1:]
    parts = _apply_sep(text, sep, is_rx)
    if len(parts) <= 1:  # separator didn't apply; try the next one
        return _split_recursive(text, rest, chunk_size, measure)

    pieces: list[str] = []
    for part in parts:
        if not part:
            continue
        if measure(part) > chunk_size:
            pieces.extend(_split_recursive(part, rest, chunk_size, measure))
        else:
            pieces.append(part)
    return pieces


# --- merging ----------------------------------------------------------------


def _merge(pieces: list[str], chunk_size: int, measure) -> list[str]:
    """Greedily merge consecutive pieces forward up to chunk_size."""
    merged: list[str] = []
    cur = ""
    for p in pieces:
        if cur and measure(cur + p) > chunk_size:
            merged.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        merged.append(cur)
    return merged


# --- vector store -----------------------------------------------------------

# Fixed namespace so uuid5(source, chunk_index) is stable across processes.
_ID_NAMESPACE = uuid.UUID("b6e3f4a2-1c5d-4e8a-9f0b-7d2c3a4e5f60")
_DENSE = "dense"   # named dense vector in the collection
_SPARSE = "sparse"  # named sparse (bm25) vector in the collection


class VectorStore:
    """Hybrid (dense + sparse) Qdrant vector store for ``chunk_documents`` output.

    Wraps ``qdrant-client[fastembed]`` (install via the ``[rag]`` extra). Embeds
    each chunk's ``document`` field with a dense model (``BAAI/bge-small-en-v1.5``)
    and a sparse BM25 model (``Qdrant/bm25``), both running locally on
    onnxruntime — no torch. Search fuses the two with Reciprocal Rank Fusion.
    See https://qdrant.github.io/fastembed/examples/Supported_Models/ for other
    models the fastembed integration supports without heavy dependencies.

    Point ids are ``uuid5(source, chunk_index)`` — deterministic, so re-adding the
    same chunk updates it in place (idempotent, no duplicates). Users address
    chunks by the natural ``(source, chunk_index)`` coordinate; the UUID is
    internal. The full chunk dict is stored verbatim as the point payload, so any
    extra keys (e.g. ``parent_id``, ``page``) are preserved and filterable.

    >>> store = VectorStore()                       # in-memory, zero setup
    >>> store.add(chunk_documents("notes.md"))
    >>> store.retrieve("how do I install?", limit=3)
    >>> store.lookup("notes.md", chunk_index=[2, 3, 4])  # small-to-large window
    """

    def __init__(
        self,
        collection: str = "free_lunch",
        location: str = ":memory:",
        dense_model: str = "BAAI/bge-small-en-v1.5",
        sparse_model: str = "Qdrant/bm25",
    ):
        try:
            from qdrant_client import QdrantClient, models
        except ImportError as exc:  # pragma: no cover - import-guard
            raise ImportError(
                "VectorStore requires qdrant-client[fastembed]. "
                'Install it with: pip install "free-lunch-ai[rag]"'
            ) from exc

        self._models = models
        self.collection = collection
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self._client = self._connect(QdrantClient, location)

    @staticmethod
    def _connect(QdrantClient, location: str):
        """``:memory:`` → in-process, ``http(s)://`` → remote (reads
        ``QDRANT_API_KEY`` from env), anything else → on-disk path."""
        if location == ":memory:":
            return QdrantClient(":memory:")
        if location.startswith(("http://", "https://")):
            return QdrantClient(url=location, api_key=os.getenv("QDRANT_API_KEY"))
        return QdrantClient(path=location)

    # --- ids ----------------------------------------------------------------

    @staticmethod
    def _point_id(source: str, chunk_index) -> str:
        return str(uuid.uuid5(_ID_NAMESPACE, f"{source}::{chunk_index}"))

    # --- collection ---------------------------------------------------------

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self.collection):
            return
        models = self._models
        self._client.create_collection(
            collection_name=self.collection,
            vectors_config={
                _DENSE: models.VectorParams(
                    size=self._client.get_embedding_size(self.dense_model),
                    distance=models.Distance.COSINE,
                )
            },
            # IDF modifier: BM25 needs document-frequency weighting computed server-side.
            sparse_vectors_config={
                _SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )

    def _source_filter(self, source: str | None):
        if source is None:
            return None
        models = self._models
        return models.Filter(
            must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
        )

    # --- CRUD ---------------------------------------------------------------

    def add(self, chunks: list[dict] | dict) -> list[str]:
        """Upsert chunk dicts. Each must have ``source`` and ``chunk_index``;
        its ``document`` is embedded. Returns the point ids. Idempotent."""
        if isinstance(chunks, dict):
            chunks = [chunks]
        if not chunks:
            return []
        self._ensure_collection()

        models = self._models
        points, ids = [], []
        for chunk in chunks:
            if "source" not in chunk or "chunk_index" not in chunk:
                raise ValueError(
                    "each chunk needs 'source' and 'chunk_index' "
                    f"(to derive its id); got keys {sorted(chunk)}"
                )
            pid = self._point_id(chunk["source"], chunk["chunk_index"])
            text = chunk.get("document", "")
            points.append(
                models.PointStruct(
                    id=pid,
                    vector={
                        _DENSE: models.Document(text=text, model=self.dense_model),
                        _SPARSE: models.Document(text=text, model=self.sparse_model),
                    },
                    payload=dict(chunk),
                )
            )
            ids.append(pid)

        self._client.upsert(collection_name=self.collection, points=points)
        return ids

    def retrieve(self, query: str, limit: int = 5, source: str | None = None) -> list[dict]:
        """Hybrid semantic search (dense + BM25, RRF fusion). Optional ``source``
        filter. Returns ``[{"id", "score", "document", "source", "chunk_index", ...}]``
        ranked best-first. Empty list if nothing has been added yet."""
        if not self._client.collection_exists(self.collection):
            return []
        models = self._models
        # With prefetch + fusion, the outer query_filter is NOT applied to the
        # prefetched candidates — the filter must live inside each Prefetch.
        flt = self._source_filter(source)
        result = self._client.query_points(
            collection_name=self.collection,
            prefetch=[
                models.Prefetch(
                    query=models.Document(text=query, model=self.dense_model),
                    using=_DENSE,
                    limit=limit,
                    filter=flt,
                ),
                models.Prefetch(
                    query=models.Document(text=query, model=self.sparse_model),
                    using=_SPARSE,
                    limit=limit,
                    filter=flt,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        return [{"id": p.id, "score": p.score, **(p.payload or {})} for p in result.points]

    def lookup(self, source: str, chunk_index: int | list[int] | None = None) -> list[dict]:
        """Exact fetch, no embedding. ``chunk_index=None`` → all chunks of
        ``source`` (paginated, no cap); an int → that one chunk; a list/tuple →
        those chunks. Returns ``[{"id", "document", "source", "chunk_index", ...}]``.
        ``chunk_index`` must match the type used in ``add`` (ints, as emitted by
        ``chunk_documents``) — ``2`` and ``2.0`` derive different ids."""
        if not self._client.collection_exists(self.collection):
            return []

        if chunk_index is None:  # all chunks of this source — paginated scan
            records = []
            offset = None
            flt = self._source_filter(source)
            while True:
                page, offset = self._client.scroll(
                    collection_name=self.collection,
                    scroll_filter=flt,
                    with_payload=True,
                    limit=256,
                    offset=offset,
                )
                records.extend(page)
                if offset is None:  # no more pages
                    break
        else:  # known coordinate(s) — recompute id(s), direct fetch
            indices = chunk_index if isinstance(chunk_index, (list, tuple)) else [chunk_index]
            ids = [self._point_id(source, i) for i in indices]
            records = self._client.retrieve(
                collection_name=self.collection, ids=ids, with_payload=True
            )
        return [{"id": r.id, **(r.payload or {})} for r in records]

    def delete(self, ids: list[str] | None = None, source: str | None = None) -> None:
        """Delete points by explicit ``ids`` or by ``source`` filter. ``ids``
        takes precedence when given (an empty list deletes nothing)."""
        if not self._client.collection_exists(self.collection):
            return
        models = self._models
        if ids is not None:
            selector = models.PointIdsList(points=ids)
        elif source is not None:
            selector = models.FilterSelector(filter=self._source_filter(source))
        else:
            raise ValueError("delete requires either ids or source")
        self._client.delete(collection_name=self.collection, points_selector=selector)
