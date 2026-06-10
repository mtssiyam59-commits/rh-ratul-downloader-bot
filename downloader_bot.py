import os
import re
import asyncio
import yt_dlp
import imageio_ffmpeg
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pyrogram import Client

# ========================= CONFIG =========================
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN")
API_ID          = int(os.environ.get("API_ID", 0))
API_HASH        = os.environ.get("API_HASH")
STORAGE_CHANNEL = os.environ.get("STORAGE_CHANNEL", "@rh_ratul_storage")

DOWNLOAD_DIR    = "./downloads"
COOKIES_FILE    = "cookies.txt"
CREDIT          = "👨‍💻 Developer : RH .RATUL"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

pyro_app = None

async def get_pyro_client():
    global pyro_app
    if pyro_app is None or not pyro_app.is_connected:
        pyro_app = Client("rh_ratul_session", api_id=API_ID, api_hash=API_HASH, bot_token=TELEGRAM_TOKEN)
        await pyro_app.start()
    return pyro_app

# ====================== ADVANCED DOWNLOAD ======================
def download_video(url, output_path):
    ydl_opts = {
        "format": "best[height<=480]/bv*[height<=480]+ba/best[height<=360]/18/bestvideo+bestaudio/best",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "ffmpeg_location": FFMPEG,
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios", "android_embedded", "web_embedded"],
            }
        },
        "retries": 15,
        "fragment_retries": 15,
        "sleep_interval": 10,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.lower().endswith(".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"
        return filename, info

def cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except:
            pass

def extract_url(message):
    if not message: return None
    text = message.text or message.caption or ""
    urls = re.findall(r'https?://[^\s\)]+', text)
    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == "text_link":
            urls.append(entity.url)
        elif entity.type == "url":
            urls.append(text[entity.offset:entity.offset + entity.length])
    for u in urls:
        if "youtube.com" in u or "youtu.be" in u:
            return u
    return urls[0] if urls else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 **RH Ratul Downloader Bot**\n\nলিংক পাঠান...", parse_mode="Markdown")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    url = extract_url(message)
    if not url:
        await message.reply_text("⚠️ লিংক পাওয়া যায়নি।")
        return

    status = await message.reply_text("⏳ ডাউনলোড হচ্ছে...\nদয়া করে অপেক্ষা করুন...", parse_mode="Markdown")
    
    uid = str(message.chat_id)
    raw_path = f"{DOWNLOAD_DIR}/{uid}_raw.mp4"

    try:
        # Small delay to avoid rate limit
        await asyncio.sleep(3)
        
        filename, info = download_video(url, raw_path)
        title = info.get("title", "Video")
        duration = info.get("duration", 0)
        dur_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
        size_mb = round(os.path.getsize(filename) / (1024 * 1024), 1)

        await status.edit_text("📤 আপলোড হচ্ছে...", parse_mode="Markdown")

        pyro = await get_pyro_client()
        sent = await pyro.send_video(
            chat_id=STORAGE_CHANNEL,
            video=filename,
            caption=f"🎬 {title}\n⏱️ {dur_str} | ~480p\n📦 {size_mb} MB\n\n{CREDIT}",
            supports_streaming=True
        )

        link = f"https://t.me/{STORAGE_CHANNEL.strip('@')}/{sent.id}"
        await status.edit_text(
            f"✅ **সফল হয়েছে!**\n\n🎬 {title}\n⏱️ {dur_str}\n[▶️ দেখুন]({link})\n\n{CREDIT}",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        error = str(e)[:400]
        if "403" in error or "Sign in" in error:
            error = "Cookie expired. Cookies আপডেট করুন।"
        await status.edit_text(f"❌ এরর:\n`{error}`", parse_mode="Markdown")
    finally:
        cleanup(raw_path)

def main():
    print("🚀 RH Ratul Downloader Bot চালু হয়েছে...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, download_handler))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
