"""Tests for free_lunch.rag.chunk_documents.

Run: python -m unittest tests/test_rag.py

Uses tiny chunk_size / overlap so expected chunk boundaries are easy to verify
by hand. Covers: raw strings, word counting, custom tokenizer, separators,
overlap, multi-source indexing, and the source auto-detection (file, directory,
glob across mixed extensions). No network or [rag]-extra parsers required —
fixtures are plain-text files only.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from free_lunch.rag import chunk_documents


class TestChunkBasics(unittest.TestCase):
    def test_output_schema_exact_keys(self):
        chunks = chunk_documents("alpha beta gamma delta", chunk_size=2, overlap=0)
        self.assertTrue(chunks)
        for c in chunks:
            self.assertEqual(set(c), {"document", "source", "chunk_index"})
            self.assertIsInstance(c["document"], str)
            self.assertTrue(c["document"].strip(), "chunk text must never be empty")

    def test_word_count_chunking(self):
        # 6 words, size 2, no overlap, no structure -> 3 chunks of 2 words.
        chunks = chunk_documents(
            "one two three four five six", chunk_size=2, overlap=0, separators=None
        )
        self.assertEqual([c["document"] for c in chunks], ["one two", "three four", "five six"])

    def test_chunk_index_is_sequential_per_source(self):
        chunks = chunk_documents(
            "a b c d e f", chunk_size=2, overlap=0, separators=None
        )
        self.assertEqual([c["chunk_index"] for c in chunks], [0, 1, 2])
        self.assertTrue(all(c["source"] == "raw_0" for c in chunks))

    def test_overlap_prepends_previous_words(self):
        # size 3, overlap 1: each chunk after the first starts with the last
        # word of the previous chunk.
        chunks = chunk_documents(
            "w1 w2 w3 w4 w5 w6", chunk_size=3, overlap=1, separators=None
        )
        texts = [c["document"] for c in chunks]
        self.assertEqual(texts[0], "w1 w2 w3")
        # second chunk core is "w4 w5 w6", prepended with overlap word "w3"
        self.assertTrue(texts[1].startswith("w3 "))

    def test_custom_tokenizer_char_count(self):
        # Measure by characters instead of words.
        chunks = chunk_documents(
            "hello world foo bar", chunk_size=8, overlap=0, tokenizer=len, separators=None
        )
        for c in chunks:
            self.assertLessEqual(len(c["document"]), 8 + 4)  # small slack for word boundary

    def test_short_text_single_chunk(self):
        chunks = chunk_documents("tiny doc", chunk_size=512, overlap=64)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["document"], "tiny doc")


class TestSeparators(unittest.TestCase):
    def test_default_splits_on_blank_lines(self):
        text = "para one here\n\npara two here\n\npara three here"
        chunks = chunk_documents(text, chunk_size=3, overlap=0)
        self.assertEqual(len(chunks), 3)

    def test_custom_literal_separator(self):
        chunks = chunk_documents(
            "a|b|c|d", chunk_size=1, overlap=0, separators=["|"], tokenizer=len
        )
        # each segment is tiny; verify all original tokens survive
        joined = " ".join(c["document"] for c in chunks)
        for tok in ("a", "b", "c", "d"):
            self.assertIn(tok, joined)


class TestMultiSource(unittest.TestCase):
    def test_list_of_raw_strings_indexed_independently(self):
        chunks = chunk_documents(
            ["first doc text", "second doc text"], chunk_size=512
        )
        sources = [c["source"] for c in chunks]
        self.assertIn("raw_0", sources)
        self.assertIn("raw_1", sources)
        # each source restarts chunk_index at 0
        for name in ("raw_0", "raw_1"):
            idxs = [c["chunk_index"] for c in chunks if c["source"] == name]
            self.assertEqual(idxs[0], 0)


class TestFileSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # mixed extensions; .pyc is binary-ish noise a glob should be able to skip
        self._write("notes.md", "# Title\n" + "word " * 10)
        self._write("data.txt", "plain text " * 10)
        self._write("script.py", "x = 1\n" * 10)
        self._write("ignore.pyc", "\x00\x01binary junk\x00")
        # nested file to exercise ** recursion vs single-level *
        os.makedirs(os.path.join(self.tmp, "sub"))
        self._write(os.path.join("sub", "deep.md"), "nested " * 10)

    def _write(self, rel, content):
        p = os.path.join(self.tmp, rel)
        Path(p).write_text(content, encoding="utf-8")
        return p

    def test_single_file(self):
        p = os.path.join(self.tmp, "notes.md")
        chunks = chunk_documents(p, chunk_size=512)
        self.assertTrue(chunks)
        self.assertEqual(chunks[0]["source"], p)

    def test_directory_reads_every_file(self):
        # directory walk reads ALL files recursively, including .pyc and nested
        chunks = chunk_documents(self.tmp, chunk_size=512)
        sources = {c["source"] for c in chunks}
        self.assertTrue(any(s.endswith("notes.md") for s in sources))
        self.assertTrue(any(s.endswith("script.py") for s in sources))
        self.assertTrue(any(s.endswith(os.path.join("sub", "deep.md")) for s in sources))

    def test_glob_selects_single_extension(self):
        pattern = os.path.join(self.tmp, "*.md")
        chunks = chunk_documents(pattern, chunk_size=512)
        sources = {c["source"] for c in chunks}
        # only top-level .md, no .py / .txt / .pyc / nested
        self.assertEqual(sources, {os.path.join(self.tmp, "notes.md")})

    def test_glob_excludes_pyc_when_selecting_py(self):
        pattern = os.path.join(self.tmp, "*.py")
        chunks = chunk_documents(pattern, chunk_size=512)
        sources = {c["source"] for c in chunks}
        self.assertEqual(sources, {os.path.join(self.tmp, "script.py")})
        self.assertFalse(any(s.endswith(".pyc") for s in sources))

    def test_recursive_glob_descends(self):
        single = os.path.join(self.tmp, "*.md")
        recursive = os.path.join(self.tmp, "**", "*.md")
        single_sources = {c["source"] for c in chunk_documents(single, chunk_size=512)}
        rec_sources = {c["source"] for c in chunk_documents(recursive, chunk_size=512)}
        self.assertNotIn(
            os.path.join(self.tmp, "sub", "deep.md"), single_sources
        )
        self.assertIn(os.path.join(self.tmp, "sub", "deep.md"), rec_sources)

    def test_empty_glob_yields_nothing(self):
        pattern = os.path.join(self.tmp, "*.nonexistent")
        self.assertEqual(chunk_documents(pattern, chunk_size=512), [])

    def test_mixed_list_file_glob_and_raw(self):
        md = os.path.join(self.tmp, "notes.md")
        chunks = chunk_documents(
            [md, os.path.join(self.tmp, "*.py"), "some raw text"], chunk_size=512
        )
        sources = {c["source"] for c in chunks}
        self.assertIn(md, sources)
        self.assertIn(os.path.join(self.tmp, "script.py"), sources)
        self.assertIn("raw_0", sources)


try:
    import qdrant_client  # noqa: F401
    from free_lunch.rag import VectorStore

    _HAS_QDRANT = True
except ImportError:
    _HAS_QDRANT = False


@unittest.skipUnless(_HAS_QDRANT, "needs the [rag] extra (qdrant-client[fastembed])")
class TestVectorStore(unittest.TestCase):
    """In-memory hybrid store — no server, no network, no API key. First run
    downloads the dense (bge-small, 67MB) + sparse (bm25, 10MB) models once."""

    @classmethod
    def setUpClass(cls):
        # One store/collection shared across read-only tests; mutating tests
        # use their own collection name so they don't interfere.
        cls.docs = [
            {"document": "Cats are independent pets that groom themselves.",
             "source": "animals.md", "chunk_index": 0},
            {"document": "Dogs are loyal companions that need daily walks.",
             "source": "animals.md", "chunk_index": 1},
            {"document": "Python is a high-level programming language.",
             "source": "tech.md", "chunk_index": 0},
        ]

    def _store(self, name):
        return VectorStore(collection=name, location=":memory:")

    def test_add_returns_ids_and_is_idempotent(self):
        store = self._store("idem")
        ids1 = store.add(self.docs)
        self.assertEqual(len(ids1), 3)
        # re-add identical chunks -> same ids, count unchanged (upsert, no dup)
        ids2 = store.add(self.docs)
        self.assertEqual(ids1, ids2)
        self.assertEqual(len(store.lookup("animals.md")) + len(store.lookup("tech.md")), 3)

    def test_add_missing_keys_raises(self):
        store = self._store("bad")
        with self.assertRaises(ValueError):
            store.add({"document": "no coordinate"})

    def test_retrieve_ranks_relevant_chunk_first(self):
        store = self._store("retr")
        store.add(self.docs)
        hits = store.retrieve("feline grooming behavior", limit=3)
        self.assertTrue(hits)
        self.assertEqual(set(hits[0]) >= {"id", "score", "document", "source", "chunk_index"}, True)
        # the cat chunk should rank above the python chunk for this query
        self.assertEqual(hits[0]["source"], "animals.md")
        self.assertIn("Cats", hits[0]["document"])

    def test_retrieve_source_filter(self):
        store = self._store("filt")
        store.add(self.docs)
        hits = store.retrieve("language", limit=5, source="tech.md")
        self.assertTrue(hits)
        self.assertTrue(all(h["source"] == "tech.md" for h in hits))

    def test_lookup_forms(self):
        store = self._store("look")
        store.add(self.docs)
        # all chunks of a source
        self.assertEqual(len(store.lookup("animals.md")), 2)
        # single int
        one = store.lookup("animals.md", chunk_index=1)
        self.assertEqual(len(one), 1)
        self.assertEqual(one[0]["chunk_index"], 1)
        self.assertIn("Dogs", one[0]["document"])
        # list (small-to-large window)
        many = store.lookup("animals.md", chunk_index=[0, 1])
        self.assertEqual({r["chunk_index"] for r in many}, {0, 1})

    def test_delete_by_source_and_by_id(self):
        store = self._store("del")
        ids = store.add(self.docs)
        store.delete(source="animals.md")
        self.assertEqual(store.lookup("animals.md"), [])
        self.assertEqual(len(store.lookup("tech.md")), 1)
        # delete remaining by explicit id
        store.delete(ids=[ids[2]])
        self.assertEqual(store.lookup("tech.md"), [])

    def test_lookup_all_paginates_beyond_one_page(self):
        # lookup(source) must return ALL chunks, not just the first scroll page.
        store = self._store("page")
        big = [{"document": f"chunk {i} body text", "source": "big.md",
                "chunk_index": i} for i in range(300)]
        store.add(big)
        self.assertEqual(len(store.lookup("big.md")), 300)

    def test_empty_store_returns_empty(self):
        store = self._store("empty")
        self.assertEqual(store.retrieve("anything"), [])
        self.assertEqual(store.lookup("nope.md"), [])

    def test_add_empty_is_noop(self):
        store = self._store("noop")
        self.assertEqual(store.add([]), [])

    def test_extra_metadata_preserved(self):
        store = self._store("meta")
        store.add({"document": "chunk with extras", "source": "x.md",
                   "chunk_index": 0, "parent_id": "doc-7", "page": 3})
        rec = store.lookup("x.md", chunk_index=0)[0]
        self.assertEqual(rec["parent_id"], "doc-7")
        self.assertEqual(rec["page"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
