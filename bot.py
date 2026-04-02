import asyncio
import os
import tempfile

import stoat
from stoat.ext.commands import Bot, command
import vk_audio

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN, prefix="!")

queue = []
voice_client = None

vk = vk_audio.VKAudio()

@bot.event
async def on_ready():
    print(f"✅ Музыкальный бот успешно запущен на Railway, Босс. ({bot.user})")

@bot.command()
async def play(ctx, *, query: str):
    global voice_client

    if not ctx.author.voice:
        await ctx.send("❗ Вы должны находиться в голосовом канале.")
        return

    if voice_client is None or not voice_client.is_connected():
        voice_client = await ctx.author.voice.channel.connect()

    await ctx.send(f"🔍 Ищу в VK: **{query}**...")

    try:
        results = vk.search(query, count=1)
        if not results:
            await ctx.send("❌ Трек не найден в VK.")
            return

        track = results[0]
        title = f"{track.get('artist', 'Unknown')} — {track.get('title', 'Unknown')}"
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
    global voice_client
    if not queue:
        await ctx.send("Очередь пуста.")
        return

    title, file_path = queue.pop(0)
    await ctx.send(f"▶️ Сейчас играет: **{title}**")

    source = stoat.FFmpegPCMAudio(file_path, executable="ffmpeg")
    voice_client.play(source, after=lambda e: asyncio.create_task(after_play(ctx, file_path)))

async def after_play(ctx, file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    await asyncio.sleep(0.5)
    await play_next(ctx)

@bot.command()
async def stop(ctx):
    global queue
    if voice_client and voice_client.is_connected():
        voice_client.stop()
    queue.clear()
    await ctx.send("⏹️ Воспроизведение остановлено.")

@bot.command()
async def leave(ctx):
    global voice_client, queue
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None
    queue.clear()
    await ctx.send("👋 Бот покинул голосовой канал.")

if __name__ == "__main__":
    bot.run()
