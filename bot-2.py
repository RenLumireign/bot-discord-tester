"""
Discord AI Chatbot Template
============================
a simple discord bot that uses Groq API to chat with your server members.
clone it, fill in the .env file, and you're good to go.

what you need:
- discord.py
- groq
- python-dotenv

quick start:
1. copy .env.example to .env and fill in your keys
2. pip install -r requirements.txt
3. python bot.py
"""

import os
import time
import sqlite3
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIG =====
# Edit these to customize your bot

BOT_NAME = os.getenv("BOT_NAME", "Enki")
BOT_PERSONALITY = os.getenv("BOT_PERSONALITY", (
    "You are a helpful, friendly AI assistant. "
    "You are concise, smart, and occasionally witty. "
    "Always detect the user's language and reply in the same language."
))
BOT_CREATOR = os.getenv("BOT_CREATOR", "Anonymous")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
ACTIVE_CHANNEL = os.getenv("ACTIVE_CHANNEL", "ai-chat")  # channel name where bot is always active
MEMORY_LIMIT = int(os.getenv("MEMORY_LIMIT", "15"))  # how many messages to remember per user
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "3"))  # cooldown between AI responses

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

# ===== VALIDATION =====
if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in .env file!")
if not GROQ_KEY:
    raise ValueError("GROQ_KEY is not set in .env file!")

# ===== SETUP =====
groq_client = Groq(api_key=GROQ_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

START_TIME = time.time()

# ===== DATABASE =====

_db_conn = None
_cooldown = {}  # user_id -> last message timestamp


def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    global _db_conn
    if _db_conn is not None:
        try:
            _db_conn.execute("SELECT 1")
            return _db_conn
        except Exception:
            _db_conn = None

    db_path = os.getenv("DB_PATH", "chatbot.db")
    _db_conn = sqlite3.connect(db_path)
    _db_conn.row_factory = sqlite3.Row
    return _db_conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role    TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    print("[DB] Database initialized")


def load_memory(user_id: str) -> list:
    """Load recent chat history for a user."""
    conn = get_db()
    rows = conn.execute("""
        SELECT role, content FROM (
            SELECT id, role, content FROM memory
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id ASC
    """, (user_id, MEMORY_LIMIT)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def save_message(user_id: str, role: str, content: str):
    """Save a message to chat history."""
    conn = get_db()
    conn.execute(
        "INSERT INTO memory (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    # Keep only the last MEMORY_LIMIT messages per user
    conn.execute("""
        DELETE FROM memory WHERE user_id = ? AND id NOT IN (
            SELECT id FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT ?
        )
    """, (user_id, user_id, MEMORY_LIMIT))
    conn.commit()


def reset_memory(user_id: str):
    """Clear chat history for a user."""
    conn = get_db()
    conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
    conn.commit()


def get_message_count(user_id: str) -> dict:
    """Get message statistics for a user."""
    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) FROM memory WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    user_msgs = conn.execute(
        "SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'user'", (user_id,)
    ).fetchone()[0]
    ai_msgs = conn.execute(
        "SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'assistant'", (user_id,)
    ).fetchone()[0]
    return {"total": total, "user": user_msgs, "ai": ai_msgs}


# ===== AI =====

async def get_ai_response(user_id: str, user_message: str) -> str:
    """Get AI response for a user message."""
    history = load_memory(user_id)

    try:
        response = groq_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": BOT_PERSONALITY}
            ] + history + [
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content or "I couldn't generate a response. Please try again."
    except Exception as e:
        print(f"[AI] Error: {e}")
        return "Sorry, I'm having trouble connecting to the AI. Please try again later."


# ===== BOT SETUP =====

bot = commands.Bot(command_prefix="!", intents=intents)
active_channels = {}  # channel_id -> user_id (channels where bot is active via wake word)


# ===== EVENTS =====

@bot.event
async def on_ready():
    print(f"[BOT] {bot.user} is online!")
    print(f"[BOT] Active channel: #{ACTIVE_CHANNEL}")
    print(f"[BOT] AI Model: {AI_MODEL}")
    init_db()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    user_id = str(message.author.id)
    text = message.content.lower()

    # Wake word: "hey <botname>" or "<botname> wake up"
    wake_words = [f"hey {BOT_NAME.lower()}", f"{BOT_NAME.lower()} wake up"]
    if any(w in text for w in wake_words):
        active_channels[message.channel.id] = user_id
        embed = discord.Embed(
            description=f"Hey! I'm {BOT_NAME}, your AI assistant. How can I help? 👋",
            color=0x5865F2
        )
        await message.channel.send(embed=embed)
        return

    # Stop word: "stop <botname>" or "<botname> stop"
    stop_words = [f"stop {BOT_NAME.lower()}", f"{BOT_NAME.lower()} stop"]
    if any(w in text for w in stop_words):
        if message.channel.id in active_channels:
            del active_channels[message.channel.id]
            await message.channel.send(f"Got it, going quiet! 👋")
        return

    # Only respond in active channel or channels activated by wake word
    is_active_channel = (
        message.channel.name == ACTIVE_CHANNEL or
        message.channel.id in active_channels
    )
    if not is_active_channel:
        return

    # Cooldown check
    now = time.time()
    last = _cooldown.get(user_id, 0)
    if (now - last) < COOLDOWN_SECONDS:
        sisa = round(COOLDOWN_SECONDS - (now - last), 1)
        await message.reply(
            f"⏳ Please wait {sisa}s!",
            mention_author=False,
            delete_after=2
        )
        return
    _cooldown[user_id] = now

    # Get AI response
    async with message.channel.typing():
        save_message(user_id, "user", message.content)
        reply = await get_ai_response(user_id, message.content)
        save_message(user_id, "assistant", reply)

        if len(reply) > 2000:
            reply = reply[:1990] + "..."

        embed = discord.Embed(description=reply, color=0x5865F2)
        embed.set_footer(text=f"{BOT_NAME} • AI Chatbot")
        await message.reply(embed=embed, mention_author=False)


# ===== COMMANDS =====

bot.remove_command("help")


@bot.command(name="help", help="Show all commands")
async def help_command(ctx, *, command: str = None):
    if command:
        cmd = bot.get_command(command)
        if not cmd:
            await ctx.send(f"Command `{command}` not found.")
            return
        embed = discord.Embed(title=f"📖 !{cmd.name}", color=0x5865F2)
        embed.add_field(name="Usage", value=f"`{cmd.usage or 'See description'}`", inline=False)
        embed.add_field(name="Description", value=cmd.help or "No description", inline=False)
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"📚 {BOT_NAME} Help",
        description=f"An AI chatbot powered by Groq.\nType `!help <command>` for details.",
        color=0x5865F2
    )
    embed.add_field(
        name="💬 Chat",
        value=f"Talk to me in #{ACTIVE_CHANNEL} or say `hey {BOT_NAME}` in any channel!",
        inline=False
    )
    embed.add_field(
        name="⚙️ Commands",
        value="`ping` `reset` `stats` `uptime`",
        inline=False
    )
    embed.set_footer(text=f"{BOT_NAME} • Made by {BOT_CREATOR}")
    await ctx.send(embed=embed)


@bot.command(name="ping", help="Check bot latency", usage="!ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        description=f"🏓 Pong! Latency: `{latency}ms`",
        color=0x00ff99
    )
    await ctx.send(embed=embed)


@bot.command(name="reset", help="Reset your chat history", usage="!reset")
async def reset(ctx):
    user_id = str(ctx.author.id)
    reset_memory(user_id)
    embed = discord.Embed(
        description=f"🧹 Your chat history has been cleared. Fresh start!",
        color=0x00ff99
    )
    await ctx.send(embed=embed)


@bot.command(name="stats", help="Show your chat statistics", usage="!stats")
async def stats(ctx):
    user_id = str(ctx.author.id)
    counts = get_message_count(user_id)

    embed = discord.Embed(title="📊 Your Stats", color=0x5865F2)
    embed.add_field(name="Total Messages", value=f"`{counts['total']}`", inline=True)
    embed.add_field(name="Your Messages", value=f"`{counts['user']}`", inline=True)
    embed.add_field(name=f"{BOT_NAME}'s Replies", value=f"`{counts['ai']}`", inline=True)
    embed.set_footer(text=f"Stats for {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name="uptime", help="Show bot uptime", usage="!uptime")
async def uptime(ctx):
    seconds = int(time.time() - START_TIME)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    embed = discord.Embed(
        title="⏱️ Uptime",
        description=f"`{days}d {hours}h {minutes}m {secs}s`",
        color=0x5865F2
    )
    await ctx.send(embed=embed)


# ===== RUN =====
bot.run(TOKEN)
