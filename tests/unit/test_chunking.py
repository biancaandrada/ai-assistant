from app.utils.chunking import chunk_text


def test_short_text_returns_one_chunk():
    chunks = chunk_text("hello world", chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].index == 0


def test_long_text_is_split():
    text = "para one.\n\n" + "para two is longer. " * 100
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c.text) <= 220 for c in chunks)


def test_overlap_preserves_context():
    text = "A" * 500
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 3


def test_empty_input_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n   ") == []


def test_invalid_args_raise():
    import pytest
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=10, overlap=10)
