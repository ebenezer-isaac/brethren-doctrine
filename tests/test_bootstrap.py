"""Tests for embeddings.bootstrap."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import embeddings.bootstrap as bootstrap_mod
from embeddings.bootstrap import (
    VOYAGE_OUTPUT_DIMENSION,
    _embed_with_voyage,
    bootstrap_qdrant_collection,
)


def test_voyage_dimension_constant_is_1024() -> None:
    assert VOYAGE_OUTPUT_DIMENSION == 1024


def test_bootstrap_unknown_store_raises() -> None:
    with pytest.raises(ValueError, match="unknown store"):
        bootstrap_qdrant_collection("invalid")  # type: ignore[arg-type]


def test_bootstrap_missing_env_var_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QDRANT_LEXICAL_URL", raising=False)
    with pytest.raises(ValueError, match="QDRANT_LEXICAL_URL"):
        bootstrap_qdrant_collection("lexical")


def test_bootstrap_lexical_creates_collection_and_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_LEXICAL_URL", "http://localhost:7100")
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])

    with patch.object(bootstrap_mod, "QdrantClient", return_value=mock_client):
        bootstrap_qdrant_collection("lexical")

    mock_client.create_collection.assert_called_once()
    call_kwargs = mock_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "lex_col"
    assert mock_client.create_payload_index.call_count >= 5


def test_bootstrap_cultural_creates_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_CULTURAL_URL", "http://localhost:7101")
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])

    with patch.object(bootstrap_mod, "QdrantClient", return_value=mock_client):
        bootstrap_qdrant_collection("cultural")

    call_kwargs = mock_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "cult_col"
    assert mock_client.create_payload_index.call_count >= 4


def test_bootstrap_skips_create_if_collection_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_LEXICAL_URL", "http://localhost:7100")
    existing = MagicMock()
    existing.name = "lex_col"
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[existing])

    with patch.object(bootstrap_mod, "QdrantClient", return_value=mock_client):
        bootstrap_qdrant_collection("lexical")

    mock_client.create_collection.assert_not_called()
    assert mock_client.create_payload_index.call_count >= 5


def test_embed_with_voyage_passes_output_dimension_1024() -> None:
    mock_result = MagicMock()
    mock_result.embeddings = [[0.0] * 1024]
    mock_client = MagicMock()
    mock_client.embed.return_value = mock_result

    with patch("voyageai.Client", return_value=mock_client):
        vec = _embed_with_voyage("hello", "fake-key")

    assert len(vec) == 1024
    mock_client.embed.assert_called_once()
    call_kwargs = mock_client.embed.call_args.kwargs
    assert call_kwargs["output_dimension"] == 1024
    assert call_kwargs["model"] == "voyage-3-large"


def test_bootstrap_uses_cosine_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_LEXICAL_URL", "http://localhost:7100")
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])

    with patch.object(bootstrap_mod, "QdrantClient", return_value=mock_client):
        bootstrap_qdrant_collection("lexical")

    call_kwargs = mock_client.create_collection.call_args.kwargs
    dense = call_kwargs["vectors_config"]["dense"]
    assert dense.size == 1024
