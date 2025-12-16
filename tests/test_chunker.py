from aiblox_orchestrator.chunker.models import ChunkingOptions
from aiblox_orchestrator.chunker.registry import InMemoryChunkerRegistry
from aiblox_orchestrator.chunker.simple_char_chunker import SimpleCharChunker
from aiblox_orchestrator.chunker.simple_token_chunker import SimpleTokenLikeChunker


def test_simple_token_chunker_deterministic():
    chunker = SimpleTokenLikeChunker()
    options = ChunkingOptions(max_chunk_tokens=2, overlap_tokens=1)
    text = "one two three four"
    first = chunker.chunk(text, options)
    second = chunker.chunk(text, options)
    assert [c.text for c in first] == [c.text for c in second]
    assert first[0].chunk_index == 0
    assert all(c.text.strip() for c in first)


def test_registry_default_alias():
    registry = InMemoryChunkerRegistry()
    assert registry.get("default")
    assert "simple_token_like@v1" in registry.list_ids()


def test_char_chunker_overlap_and_indices():
    chunker = SimpleCharChunker()
    options = ChunkingOptions(max_chunk_chars=4, overlap_chars=2)
    text = "abcdefgh"
    chunks = chunker.chunk(text, options)
    assert [c.text for c in chunks] == ["abcd", "cdef", "efgh"]
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert all(c.text.strip() for c in chunks)
