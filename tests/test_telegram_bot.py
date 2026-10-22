"""Tests for Telegram bot handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from src.bot.telegram_bot import cmd_clear, cmd_debug, cmd_start, handle_message


def _create_mock_update(text: str = "", chat_id: int = 12345) -> Update:
    """Helper to build a mock Telegram Update object."""
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = chat_id
    user = MagicMock(spec=User)
    user.id = chat_id

    message = MagicMock(spec=Message)
    message.text = text
    message.reply_text = AsyncMock()

    update.message = message
    update.effective_chat = chat
    update.effective_user = user
    return update


@pytest.mark.asyncio
async def test_cmd_start():
    """Verify /start clears memory and sends the welcome message."""
    update = _create_mock_update("/start")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("src.bot.telegram_bot.clear_history") as mock_clear:
        await cmd_start(update, context)
        mock_clear.assert_called_once_with("tg_12345")

    update.message.reply_text.assert_called_once()
    assert "Welcome to ResoAI" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_clear():
    """Verify /clear resets conversation history."""
    update = _create_mock_update("/clear")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("src.bot.telegram_bot.clear_history") as mock_clear:
        await cmd_clear(update, context)
        mock_clear.assert_called_once_with("tg_12345")

    update.message.reply_text.assert_called_once()
    assert "cleared" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_message_success():
    """Verify handle_message rewrites query, queries RAG, saves memory, and replies."""
    update = _create_mock_update("Who is in the AI team?")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_chat_action = AsyncMock()

    with (
        patch("src.bot.telegram_bot.rewrite_query", AsyncMock(return_value="Who is in the AI team?")) as mock_rewrite,
        patch("src.bot.telegram_bot.rag_ask", AsyncMock(return_value={"answer": "John Doe and Jane Smith.", "time_elapsed_seconds": 1.2})) as mock_ask,
        patch("src.bot.telegram_bot.add_message") as mock_add_msg,
    ):
        await handle_message(update, context)

        mock_rewrite.assert_called_once_with("tg_12345", "Who is in the AI team?")
        mock_ask.assert_called_once_with("Who is in the AI team?")
        assert mock_add_msg.call_count == 2  # user and ai messages

    update.message.reply_text.assert_called_once()
    call_text = update.message.reply_text.call_args[0][0]
    assert "John Doe and Jane Smith" in call_text
    assert "1.2s" in call_text


@pytest.mark.asyncio
async def test_cmd_debug():
    """Verify /debug displays routing output."""
    update = _create_mock_update("/debug How many people are in HR?")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["How", "many", "people", "are", "in", "HR?"]

    mock_plan = MagicMock()
    mock_plan.intent = "count"
    mock_plan.entity = "employee"
    mock_plan.search_terms = ["HR"]
    mock_plan.attribute = "department"
    mock_plan.is_structured_query = True
    mock_plan.criteria = "hr"
    mock_plan.decompose_time = 0.45

    with (
        patch("src.rag.query_decomposer.QueryDecomposer.decompose", return_value=mock_plan),
        patch("src.rag.chain._interpreter.query", return_value={"count": 5, "matches": [{"name": "Alice"}]}),
    ):
        await cmd_debug(update, context)

    # First call: acknowledge debug; second call: output debug info
    assert update.message.reply_text.call_count == 2
    final_output = update.message.reply_text.call_args_list[1][0][0]
    assert "Query Decomposer Output" in final_output
    # When DuckDB lakehouse is active, route shows DuckDB; fallback is DataInterpreter
    assert ("DuckDB Medallion Lakehouse" in final_output) or ("DataInterpreter" in final_output)
