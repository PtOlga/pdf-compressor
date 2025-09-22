#!/usr/bin/env python3
"""
Скрипт для отправки уведомлений в Telegram
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram credentials not configured")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Отправка текстового сообщения"""
        
        url = f"{self.api_url}/sendMessage"
        
        # Telegram имеет лимит 4096 символов на сообщение
        if len(text) > 4000:
            # Разбиваем на части
            return self._send_long_message(text, parse_mode)
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get('ok', False)
            
        except Exception as e:
            print(f"❌ Error sending Telegram message: {e}")
            return False
    
    def _send_long_message(self, text: str, parse_mode: str) -> bool:
        """Отправка длинного сообщения по частям"""
        
        # Разбиваем текст на части по 4000 символов
        parts = []
        current_part = ""
        
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part + line + '\n') > 4000:
                if current_part:
                    parts.append(current_part.rstrip())
                    current_part = line + '\n'
                else:
                    # Строка сама по себе больше лимита
                    parts.append(line[:4000])
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part.rstrip())
        
        # Отправляем все части
        success = True
        for i, part in enumerate(parts):
            if i == 0:
                message_text = part
            else:
                message_text = f"*(continued {i+1}/{len(parts)})*\n\n{part}"
            
            if not self.send_message(message_text, parse_mode):
                success = False
        
        return success
    
    def send_document(self, file_path: str, caption: str = "") -> bool:
        """Отправка документа"""
        
        url = f"{self.api_url}/sendDocument"
        
        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                return result.get('ok', False)
                
        except Exception as e:
            print(f"❌ Error sending document: {e}")
            return False


def load_stats(stats_path: str = 'temp/logs/stats.json') -> dict:
    """Загрузка статистики из JSON файла"""
    
    stats_file = Path(stats_path)
    if not stats_file.exists():
        return {}
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def format_file_size(bytes_size: int) -> str:
    """Форматирование размера файла"""
    if bytes_size == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def create_telegram_message(report_content: str = "", stats: dict = None) -> str:
    """Создание сообщения для Telegram"""
    
    if not stats:
        stats = {}
    
    # Определяем статус
    processed = stats.get('processed_files', 0)
    failed = stats.get('failed_files', 0)
    
    if processed > 0 and failed == 0:
        status_emoji = "✅"
        status = "SUCCESS"
    elif processed > 0 and failed > 0:
        status_emoji = "⚠️"
        status = "PARTIAL"
    elif failed > 0:
        status_emoji = "❌"
        status = "FAILED"
    else:
        status_emoji = "ℹ️"
        status = "NO FILES"
    
    # Заголовок
    message = f"{status_emoji} *PDF Compression {status}*\n\n"
    
    # Основная статистика
    message += f"📊 *Summary:*\n"
    
    if processed > 0:
        message += f"✅ Processed: *{processed}* files\n"
    
    if failed > 0:
        message += f"❌ Failed: *{failed}* files\n"
    
    # Экономия места
    if stats.get('total_bytes_saved', 0) > 0:
        saved_size = format_file_size(stats['total_bytes_saved'])
        percent_saved = stats.get('total_percent_saved', 0)
        message += f"💾 Space saved: *{saved_size}* ({percent_saved:.1f}%)\n"
        
        if stats.get('total_size_before', 0) > 0:
            size_before = format_file_size(stats['total_size_before'])
            size_after = format_file_size(stats.get('total_size_after', 0))
            message += f"   📊 Before: {size_before}\n"
            message += f"   📊 After: {size_after}\n"
    
    # Время выполнения
    duration = stats.get('duration', 0)
    if duration > 0:
        if duration < 60:
            time_str = f"{duration:.1f} sec"
        elif duration < 3600:
            time_str = f"{duration/60:.1f} min"
        else:
            time_str = f"{duration/3600:.1f} hours"
        
        message += f"⏱️ Duration: {time_str}\n"
    
    # Настройки
    compression_level = stats.get('compression_level', 'unknown')
    message += f"🗜️ Level: {compression_level}\n"
    
    # Папки
    if stats.get('source_folder'):
        message += f"📁 Source: `{stats['source_folder']}`\n"
    if stats.get('target_folder'):
        message += f"📁 Target: `{stats['target_folder']}`\n"
    
    message += "\n"
    
    # Детали по файлам (только если немного файлов)
    files = stats.get('files', [])
    if files and len(files) <= 5:
        message += f"📄 *Files processed:*\n"
        for file_info in files:
            if isinstance(file_info, dict):
                name = file_info.get('name', 'unknown')
                percent = file_info.get('percent_saved', 0)
                message += f"• {name}: {percent:.1f}%\n"
        message += "\n"
    elif len(files) > 5:
        message += f"📄 Processed {len(files)} files\n\n"
    
    # Ошибки (первые 3)
    errors = stats.get('errors', [])
    if errors:
        message += f"❌ *Errors ({len(errors)}):*\n"
        for error in errors[:3]:
            if isinstance(error, dict):
                file_name = error.get('file', 'unknown')
                error_msg = error.get('error', 'unknown')
                # Обрезаем длинные сообщения об ошибках
                if len(error_msg) > 50:
                    error_msg = error_msg[:50] + "..."
                message += f"• {file_name}: {error_msg}\n"
            elif isinstance(error, str):
                if len(error) > 60:
                    error = error[:60] + "..."
                message += f"• {error}\n"
        
        if len(errors) > 3:
            message += f"• ... and {len(errors) - 3} more\n"
        message += "\n"
    
    # Время
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    message += f"🕒 {timestamp}"
    
    return message


def main():
    """Основная функция"""
    
    try:
        # Проверяем аргументы
        if len(sys.argv) < 2:
            print("Usage: python send_notification.py <report_file> [stats_file]")
            sys.exit(1)
        
        report_file = sys.argv[1]
        stats_file = sys.argv[2] if len(sys.argv) > 2 else 'temp/logs/stats.json'
        
        # Проверяем наличие токенов
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("ℹ️ Telegram credentials not configured, skipping notification")
            sys.exit(0)
        
        # Загружаем статистику
        stats = load_stats(stats_file)
        
        # Загружаем отчет если нужно
        report_content = ""
        if Path(report_file).exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = f.read()
        
        # Создаем уведомление
        notifier = TelegramNotifier()
        
        # Отправляем основное сообщение
        message = create_telegram_message(report_content, stats)
        
        print("📱 Sending Telegram notification...")
        success = notifier.send_message(message)
        
        if success:
            print("✅ Telegram notification sent successfully")
            
            # Отправляем детальный отчет как документ если он есть и большой
            if Path(report_file).exists() and len(report_content) > 2000:
                print("📎 Sending detailed report as document...")
                doc_success = notifier.send_document(
                    report_file, 
                    "📄 Detailed compression report"
                )
                if doc_success:
                    print("✅ Detailed report sent successfully")
                else:
                    print("⚠️ Failed to send detailed report")
        else:
            print("❌ Failed to send Telegram notification")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
