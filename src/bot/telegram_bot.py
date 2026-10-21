"""Telegram bot integration for ResoAI Agentic CRAG pipeline.

Run this bot standalone with:
    python -m src.bot.telegram_bot
or:
    python scripts/run_telegram_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import settings
from src.rag.chain import ask as rag_ask
from src.rag.memory import add_message, clear_history, rewrite_query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("resoai.telegram_bot")

WELCOME_MESSAGE = (
    "👋 *Welcome to ResoAI!* I am your Enterprise HR & Knowledge Assistant.\n\n"
    "I'm powered by an autonomous, local **Agentic CRAG (Conversational RAG)** pipeline "
    "running on-premises.\n\n"
    "💡 *Things you can ask me:*\n"
    "• *Employees:* `Who is the lead for ResoAI?`\n"
    "• *Exact Counts:* `How many people work in Jaipur?`\n"
    "• *Policies:* `What is the probation period policy?`\n"
    "• *Holidays:* `List upcoming holidays in October`\n"
    "• *Follow-up questions:* `What is his email?`\n\n"
    "🛠 *Commands:*\n"
    "/start - Show this welcome message\n"
    "/clear - Reset conversation memory\n"
    "/debug `<question>` - Check intent & routing pathway\n"
    "/help - Show help and instructions"
)

HELP_MESSAGE = (
    "🤖 *ResoAI Telegram Bot Help*\n\n"
    "*How it works:*\n"
    "ResoAI uses a dual-pathway architecture:\n"
    "1. **Deterministic Path**: Counts and directory rosters are scanned directly from verified records for 100% accuracy.\n"
    "2. **Semantic Path**: Complex policy questions and project details are retrieved using hybrid BM25 + Vector search with cross-encoder re-ranking.\n\n"
    "*Useful Commands:*\n"
    "• `/clear` or `/reset`: Clears your conversation history to start a fresh topic.\n"
    "• `/debug <question>`: Inspect how the agent decomposes your question without generating an answer.\n"
    "• `/help`: Display this help text."
)


async def _keep_typing(bot, chat_id: int, stop_event: asyncio.Event) -> None:
    """Continuously send typing indicators while RAG generation is in progress."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.5)
        except asyncio.TimeoutError:
            pass


async def safe_reply(update: Update, text: str) -> None:
    """Send text reply safely, splitting if longer than Telegram's 4096 char limit."""
    if not update.message:
        return

    # Telegram limit is 4096 characters per message
    chunk_size = 4000
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] if len(text) > chunk_size else [text]

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            # Fallback to plain text if Markdown parsing fails (e.g. unclosed backticks/stars)
            await update.message.reply_text(chunk)


# ── Command Handlers ─────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.effective_chat:
        session_id = f"tg_{update.effective_chat.id}"
        clear_history(session_id)
    await safe_reply(update, WELCOME_MESSAGE)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await safe_reply(update, HELP_MESSAGE)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear or /reset command."""
    if not update.effective_chat:
        return
    session_id = f"tg_{update.effective_chat.id}"
    clear_history(session_id)
    await safe_reply(update, "🧹 *Conversation memory cleared!* You can start a fresh topic.")


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /debug <question> command."""
    if not update.message:
        return

    args = context.args
    if not args:
        await safe_reply(update, "⚠️ Please provide a question to debug, e.g.:\n`/debug How many employees are in HR?`")
        return

    question = " ".join(args).strip()
    await safe_reply(update, f"🔍 *Debugging query:* `{question}`\n_Analyzing decomposition..._")

    try:
        from src.rag.query_decomposer import QueryDecomposer
        from src.rag.chain import _interpreter

        decomposer = QueryDecomposer()
        plan = decomposer.decompose(question)

        debug_info = [
            "🧠 *Query Decomposer Output:*",
            f"• *Intent:* `{plan.intent}`",
            f"• *Entity:* `{plan.entity}`",
            f"• *Search Terms:* `{plan.search_terms}`",
            f"• *Attribute:* `{plan.attribute}`",
            f"• *Structured Query:* `{plan.is_structured_query}`",
            f"• *Decompose Time:* `{plan.decompose_time:.2f}s`",
            "",
        ]

        if plan.is_structured_query:
            itp_result = _interpreter.query(plan.entity, plan.criteria)
            count = itp_result["count"] if itp_result else 0
            matches = itp_result["matches"][:5] if itp_result else []
            debug_info.extend([
                "⚡ *Route:* `DataInterpreter (Deterministic JSON Scan)`",
                f"• *Criteria:* `{plan.criteria}`",
                f"• *Count Match:* `{count}`",
                f"• *Sample Matches:* {len(matches)}",
            ])
        else:
            debug_info.extend([
                "📚 *Route:* `Hybrid RAG (BM25 + ChromaDB + FlashRank + LLM)`",
                "• *Retrieval Mode:* Vector Similarity + Keyword Filter",
            ])

        await safe_reply(update, "\n".join(debug_info))
    except Exception as exc:
        logger.exception("Debug command failed")
        await safe_reply(update, f"❌ Debug failed: `{str(exc)}`")


# ── Message Handler ──────────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming user text questions."""
    if not update.message or not update.message.text:
        return

    raw_question = update.message.text.strip()
    if not raw_question:
        return

    chat_id = update.effective_chat.id
    session_id = f"tg_{chat_id}"

    logger.info("Telegram [Chat: %s] received question: %s", chat_id, raw_question)

    stop_typing_event = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id, stop_typing_event))

    try:
        # Step 1: Memory rewrite (resolve pronouns like 'he', 'his', 'it')
        search_query = await rewrite_query(session_id, raw_question)
        if search_query != raw_question:
            logger.info("Rewrote '%s' -> '%s'", raw_question, search_query)

        # Step 2: Query the RAG chain
        result = await rag_ask(search_query)
        answer = result.get("answer", "No answer found.")
        elapsed = result.get("time_elapsed_seconds")

        # Step 3: Append to conversational memory
        add_message(session_id, "user", raw_question)
        add_message(session_id, "ai", answer)

        # Stop typing indicator before sending message
        stop_typing_event.set()
        await typing_task

        # Step 4: Reply with answer + optional timing footer
        reply_text = answer
        if elapsed is not None:
            reply_text += f"\n\n⏱ _Answered in {elapsed}s_"

        await safe_reply(update, reply_text)

    except Exception as exc:
        stop_typing_event.set()
        await typing_task
        logger.exception("Error processing question '%s'", raw_question)
        await safe_reply(
            update,
            "⚠️ Sorry, an error occurred while processing your question. Please try again.",
        )


# ── Bot Factory & Runner ─────────────────────────────────


def create_telegram_app(token: str) -> Application:
    """Construct and configure the Telegram application."""
    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler(["clear", "reset"], cmd_clear))
    app.add_handler(CommandHandler("debug", cmd_debug))

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    return app


def main() -> None:
    """CLI Entrypoint for the Telegram bot."""
    parser = argparse.ArgumentParser(description="ResoAI Telegram Bot Runner")
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Telegram Bot Token (or set TELEGRAM_BOT_TOKEN env var / .env)",
    )
    args = parser.parse_args()

    token = (
        args.token
        or os.environ.get("TELEGRAM_BOT_TOKEN")
        or settings.telegram_bot_token
    )

    if not token or not token.strip():
        print(
            "\n"
            "❌ ERROR: No Telegram Bot Token found!\n\n"
            "To run the bot, please provide a token using one of the following methods:\n"
            "  1. CLI parameter:   python -m src.bot.telegram_bot --token <YOUR_TOKEN>\n"
            "  2. Environment var: export TELEGRAM_BOT_TOKEN=<YOUR_TOKEN>\n"
            "  3. In .env file:    TELEGRAM_BOT_TOKEN=<YOUR_TOKEN>\n\n"
            "👉 How to get a free token in 30 seconds:\n"
            "  1. Open Telegram and search for '@BotFather'\n"
            "  2. Send '/newbot' and follow the prompts\n"
            "  3. Copy the HTTP API token BotFather gives you.\n"
        )
        sys.exit(1)

    print("=" * 60)
    print("🚀 Starting ResoAI Telegram Bot...")
    print(f"   Company: {settings.company_name}")
    print(f"   Model:   {settings.ollama_llm_model} via {settings.ollama_base_url}")
    print("=" * 60)

    app = create_telegram_app(token.strip())
    app.run_polling()


if __name__ == "__main__":
    main()
