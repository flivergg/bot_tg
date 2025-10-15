import requests
import re
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "ВАШ_ТОКЕН"

class TikTokDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.tiktok.com/',
        })

    def get_final_url(self, url):
        try:
            response = self.session.head(url, allow_redirects=True, timeout=10)
            return str(response.url)
        except:
            return url

    def method_tikwm(self, url):
        try:
            api_url = "https://www.tikwm.com/api/"
            data = {
                'url': url,
                'count': 12,
                'cursor': 0,
                'web': 1,
                'hd': 1
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://www.tikwm.com',
                'Referer': 'https://www.tikwm.com/',
            }
            
            response = self.session.post(api_url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    video_data = result.get('data', {})
                    video_url = video_data.get('hdplay') or video_data.get('play') or video_data.get('wmplay')
                    if video_url:
                        if not video_url.startswith('http'):
                            video_url = 'https://www.tikwm.com' + video_url
                        return video_url
            return None
        except Exception as e:
            logger.error(f"TikWM method error: {e}")
            return None

    def method_snaptik(self, url):
        try:
            api_url = "https://snaptik.app/action.php"
            data = {
                'url': url
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://snaptik.app',
                'Referer': 'https://snaptik.app/',
            }
            
            response = self.session.post(api_url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                json_match = re.search(r'{"status":"success".*?"url":"([^"]+)"', response.text)
                if json_match:
                    video_url = json_match.group(1).replace('\\/', '/')
                    return video_url
            return None
        except Exception as e:
            logger.error(f"SnapTik method error: {e}")
            return None

    def method_ssstik(self, url):
        """Используем ssstik.io"""
        try:
            page_url = "https://ssstik.io"
            response = self.session.get(page_url, timeout=10)
            
            token_match = re.search(r'name="tt" value="([^"]+)"', response.text)
            token = token_match.group(1) if token_match else "Y2hVeVk5"
            
            api_url = "https://ssstik.io/abc"
            data = {
                'id': url,
                'locale': 'en',
                'tt': token
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://ssstik.io',
                'Referer': 'https://ssstik.io/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.post(api_url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                video_match = re.search(r'href="([^"]*\.mp4[^"]*)"', response.text)
                if video_match:
                    video_url = video_match.group(1)
                    if not video_url.startswith('http'):
                        video_url = 'https://ssstik.io' + video_url
                    return video_url
            return None
        except Exception as e:
            logger.error(f"SSStik method error: {e}")
            return None

    def download_video(self, video_url):
        """Скачиваем видео"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.tiktok.com/',
            }
            
            response = self.session.get(video_url, headers=headers, stream=True, timeout=60)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                temp_file.close()
                
                file_size = os.path.getsize(temp_file.name)
                if file_size > 1000:  
                    return temp_file.name
                else:
                    os.unlink(temp_file.name)
                    return None
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

    def process_url(self, url):
        """Основной метод обработки"""
        methods = [
            ("TikWM", self.method_tikwm),
            ("SnapTik", self.method_snaptik),
            ("SSStik", self.method_ssstik),
        ]
        
        final_url = self.get_final_url(url)
        logger.info(f"Processing URL: {final_url}")
        
        for method_name, method_func in methods:
            try:
                logger.info(f"Trying {method_name}")
                video_url = method_func(final_url)
                if video_url:
                    logger.info(f"{method_name} success: {video_url}")
                    video_path = self.download_video(video_url)
                    if video_path:
                        return video_path, None
                    else:
                        logger.error(f"{method_name}: Failed to download video")
            except Exception as e:
                logger.error(f"{method_name} error: {e}")
                continue
                
        return None, "Не удалось скачать видео. Попробуйте другую ссылку."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот для скачивания TikTok видео\n\n"
        "Отправьте ссылку на видео в формате:\n"
        "• https://vm.tiktok.com/...\n"
        "• https://www.tiktok.com/@.../video/...\n\n"
        "Бот попробует скачать видео без водяного знака."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    
    if not any(domain in user_message for domain in ['tiktok.com', 'vm.tiktok.com']):
        await update.message.reply_text("❌ Отправьте ссылку на TikTok видео")
        return

    processing_msg = await update.message.reply_text("⏳ Обрабатываю ссылку...")

    try:
        downloader = TikTokDownloader()
        video_path, error = downloader.process_url(user_message)
        
        if error:
            await processing_msg.edit_text(f"❌ {error}")
            return

        file_size = os.path.getsize(video_path)
        if file_size > 50 * 1024 * 1024:
            await processing_msg.edit_text("❌ Видео слишком большое для Telegram (>50MB)")
            os.unlink(video_path)
            return

        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Видео скачано!",
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60
            )
        
        os.unlink(video_path)
        await processing_msg.delete()

    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text("❌ Ошибка при обработке. Попробуйте позже.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
