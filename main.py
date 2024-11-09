from telegram import InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.update import Update  # Correct import of Update class
from io import BytesIO
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import os

TELEGRAM_BOT_TOKEN = '8029641070:AAEdToybM_DN461eBtANHamSukgRvKsC-T0'
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit
ABA_QRCODE_PATH = 'qrcode.png'

# Sanitize YouTube URL
def sanitize_youtube_url(url):
    url = url.strip()
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        for param in ['fbclid', 'ref', 'tracking_id']:
            query_params.pop(param, None)
        sanitized_url = urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))
        return sanitized_url
    else:
        return None

# Download YouTube video
def download_youtube_video(video_url):
    video_url = sanitize_youtube_url(video_url)
    if not video_url:
        return None, "Unsupported URL: Please ensure it's a valid YouTube video link."
    options = {'format': 'best', 'quiet': True}
    try:
        video_data = BytesIO()
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'video')
            temp_filename = ydl.prepare_filename(info)
            ydl.download([video_url])
            with open(temp_filename, 'rb') as f:
                video_data.write(f.read())
            video_data.seek(0)
            if video_data.getbuffer().nbytes > MAX_TELEGRAM_FILE_SIZE:
                os.remove(temp_filename)
                return None, "The downloaded video exceeds Telegram's file size limit of 50 MB."
            os.remove(temp_filename)
        return video_data, f"{video_title}.mp4"
    except Exception as e:
        return None, f"Error downloading video: {e}"

# Start command handler
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("YouTube", callback_data='youtube'),
            InlineKeyboardButton("Facebook", callback_data='facebook'),
            InlineKeyboardButton("Pay Coffee Admin", callback_data='qrcode')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hello! Please select a platform to download a video from:",
        reply_markup=reply_markup
    )

# Callback handler for button selection
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'qrcode':
        # Send ABA ID message and QR code image when "Pay Coffee Admin" is clicked
        aba_id = "ABA: 004713257"  # Replace with your actual ABA ID
        caption = f"Thank you for your support! Here is my ABA for payment:\n\n{aba_id}"
        with open(ABA_QRCODE_PATH, 'rb') as qr_file:
            await query.message.reply_photo(photo=InputFile(qr_file), caption=caption)
    else:
        platform = query.data
        context.user_data['platform'] = platform
        await query.edit_message_text(f"You selected {platform.capitalize()}. Now, please send the video link.")

# Handler for receiving video URLs
async def handle_message(update: Update, context: CallbackContext):
    if 'platform' not in context.user_data:
        await update.message.reply_text("Please select a platform first by using /start.")
        return

    platform = context.user_data['platform']
    video_url = update.message.text

    if platform == "youtube":
        video_data, response = download_youtube_video(video_url)
    else:
        await update.message.reply_text("Please specify a valid platform by using /start.")
        return

    if video_data:
        await update.message.reply_video(video_data, filename=response, caption="Here is your downloaded video!")
        video_data.close()
    else:
        await update.message.reply_text(response)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    main()
