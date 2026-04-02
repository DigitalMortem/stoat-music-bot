import asyncio
import os
import tempfile
from pathlib import Path

import stoat
from stoat.ext import commands
import vk_audio

TOKEN = os.getenv("BOT_TOKEN")  # Берём токен из переменных окружения Railway

bot = commands.Bot(token=TOKEN, prefix="!")

queue = []
voice_client = None
current_player = None

vk = vk_audio.VKAudio()

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен на Railway и готов к работе, Босс.")

@bot.command()
async def play(ctx, *, query: str):
    global voice_client

    if not ctx.author.voice:
        await ctx.send("Вы должны быть в голосовом канале.")
        return

    channel = ctx.author.voice.channel
    if voice_client is None or not voice_client.is_connected():
        voice_client = await channel.connect()

    await ctx.send(f"🔍 Ищу в VK: **{query}**...")

    try:
        results = vk.search(query, count=1)
        if not results:
            await ctx.send("❌ Трек не найден.")
            return

        track = results[0]
        title = f"{track['artist']} - {track['title']}"
        await ctx.send(f"🎵 Найдено: **{title}**")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            file_path = tmp.name
            vk.download(track, file_path)

        queue.append((title, file_path))

        if not voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {str(e)}")

async def play_next(ctx):
    global current_player
    if not queue:
        return

    title, file_path = queue.pop(0)
    await ctx.send(f"▶️ Сейчас играет: **{title}**")

    source = stoat.FFmpegPCMAudio(file_path, executable="ffmpeg")
    current_player = voice_client.play(source, after=lambda e: asyncio.create_task(after_play(ctx, file_path)))

async def after_play(ctx, file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    await play_next(ctx)

@bot.command()
async def pause(ctx):
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Приостановлено.")

@bot.command()
async def resume(ctx):
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Возобновлено.")

@bot.command()
async def stop(ctx):
    global queue
    if voice_client:
        voice_client.stop()
    queue.clear()
    await ctx.send("⏹️ Остановлено.")

@bot.command()
async def leave(ctx):
    global voice_client, queue
    if voice_client:
        await voice_client.disconnect()
        voice_client = None
    queue.clear()
    await ctx.send("👋 Бот вышел из канала.")

if __name__ == "__main__":
    bot.run()