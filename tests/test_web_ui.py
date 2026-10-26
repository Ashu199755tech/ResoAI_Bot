"""Tests for Web UI endpoints and FastAPI routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_serve_web_ui():
    """Verify GET / serves the futuristic HTML interface."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "RESO AI" in response.text
    assert "NEURAL CRAG" in response.text


@pytest.mark.asyncio
async def test_reset_session_endpoint():
    """Verify POST /api/reset clears session memory."""
    with patch("src.main.clear_history") as mock_clear:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/reset", json={"session_id": "test_sess_123"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_clear.assert_called_once_with("test_sess_123")


@pytest.mark.asyncio
async def test_ask_endpoint_returns_pathway_and_sources():
    """Verify POST /api/ask includes pathway and sources metadata."""
    mock_result = {
        "answer": "There are 64 employees in HR.",
        "time_elapsed_seconds": 0.08,
        "pathway": "DuckDB Medallion Lakehouse",
        "sources": [{"record_type": "lakehouse_gold", "record_id": "duckdb_gold_mart"}],
    }

    with (
        patch("src.main.rewrite_query", AsyncMock(return_value="How many in HR?")),
        patch("src.main.rag_ask", AsyncMock(return_value=mock_result)),
        patch("src.main.add_message"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/ask", json={"question": "How many in HR?", "session_id": "test_sess"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["pathway"] == "DuckDB Medallion Lakehouse"
        assert len(data["sources"]) == 1
        assert "64 employees in HR" in data["answer"]
