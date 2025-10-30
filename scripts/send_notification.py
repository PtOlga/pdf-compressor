#!/usr/bin/env python3
"""
Script for sending Telegram notifications
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime


class TelegramNotifier:
    """Class for sending Telegram notifications"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram credentials not configured")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """Send text message"""
        
        url = f"{self.api_url}/sendMessage"
        
        # Clean message from problematic characters
        cleaned_text = self._clean_message_for_telegram(text)
        
        # Telegram has 4096 character limit per message
        if len(cleaned_text) > 4000:
            # Split into parts
            return self._send_long_message(cleaned_text, parse_mode)
        
        payload = {
            'chat_id': self.chat_id,
            'text': cleaned_text,
            'disable_web_page_preview': True
        }
        
        # Only add parse_mode if specified
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get('ok', False)
            
        except Exception as e:
            print(f"[ERROR] Error sending Telegram message: {e}")
            return False
    
    def _clean_message_for_telegram(self, text: str) -> str:
        """Clean message from problematic characters for Telegram API"""
        
        # Replace problematic emoji with text equivalents
        replacements = {
            '✅': '[SUCCESS]',
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '📊': '[STATS]',
            '📄': '[FILE]',
            '💾': '[SAVED]',
            '⏱️': '[TIME]',
            '🗜️': '[COMPRESS]',
            '📁': '[FOLDER]',
            '🕒': '[TIMESTAMP]',
            '📱': '[TELEGRAM]',
            '📎': '[ATTACH]',
            'ℹ️': '[INFO]'
        }
        
        cleaned_text = text
        for emoji, replacement in replacements.items():
            cleaned_text = cleaned_text.replace(emoji, replacement)
        
        return cleaned_text
    
    def _send_long_message(self, text: str, parse_mode: str) -> bool:
        """Send long message in parts"""
        
        # Split text into parts of 4000 characters
        parts = []
        current_part = ""
        
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part + line + '\n') > 4000:
                if current_part:
                    parts.append(current_part.rstrip())
                    current_part = line + '\n'
                else:
                    # Line itself is longer than limit
                    parts.append(line[:4000])
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part.rstrip())
        
        # Send all parts
        success = True
        for i, part in enumerate(parts):
            if i == 0:
                message_text = part
            else:
                message_text = f"(continued {i+1}/{len(parts)})\n\n{part}"
            
            if not self.send_message(message_text, parse_mode):
                success = False
        
        return success
    
    def send_document(self, file_path: str, caption: str = "") -> bool:
        """Send document"""
        
        url = f"{self.api_url}/sendDocument"
        
        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': self._clean_message_for_telegram(caption)
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                return result.get('ok', False)
                
        except Exception as e:
            print(f"[ERROR] Error sending document: {e}")
            return False


def load_stats(stats_path: str = 'temp/logs/stats.json') -> dict:
    """Load statistics from JSON file"""
    
    stats_file = Path(stats_path)
    if not stats_file.exists():
        return {}
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def format_file_size(bytes_size: int) -> str:
    """Format file size"""
    if bytes_size == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def create_telegram_message(report_content: str = "", stats: dict = None) -> str:
    """Create message for Telegram"""
    
    if not stats:
        stats = {}
    
    # Determine status
    processed = stats.get('processed_files', 0)
    failed = stats.get('failed_files', 0)
    
    if processed > 0 and failed == 0:
        status_prefix = "[SUCCESS]"
        status = "SUCCESS"
    elif processed > 0 and failed > 0:
        status_prefix = "[WARNING]"
        status = "PARTIAL"
    elif failed > 0:
        status_prefix = "[ERROR]"
        status = "FAILED"
    else:
        status_prefix = "[INFO]"
        status = "NO FILES"
    
    # Handle case when only report_content is available (no stats)
    if not stats and report_content:
        if "Error generating report" in report_content:
            return f"[ERROR] PDF Compression FAILED\n\nMain process failed to generate logs.\nCheck GitHub Actions for details.\n\n[TIMESTAMP] {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    
    # Header
    message = f"{status_prefix} PDF Compression {status}\n\n"
    
    # Main statistics
    message += f"[STATS] Summary:\n"
    
    if processed > 0:
        message += f"[SUCCESS] Processed: {processed} files\n"
    
    if failed > 0:
        message += f"[ERROR] Failed: {failed} files\n"
    
    # Space savings
    if stats.get('total_bytes_saved', 0) > 0:
        saved_size = format_file_size(stats['total_bytes_saved'])
        percent_saved = stats.get('total_percent_saved', 0)
        message += f"[SAVED] Space saved: {saved_size} ({percent_saved:.1f}%)\n"
        
        if stats.get('total_size_before', 0) > 0:
            size_before = format_file_size(stats['total_size_before'])
            size_after = format_file_size(stats.get('total_size_after', 0))
            message += f"   [STATS] Before: {size_before}\n"
            message += f"   [STATS] After: {size_after}\n"
    
    # Duration
    duration = stats.get('duration', 0)
    if duration > 0:
        if duration < 60:
            time_str = f"{duration:.1f} sec"
        elif duration < 3600:
            time_str = f"{duration/60:.1f} min"
        else:
            time_str = f"{duration/3600:.1f} hours"
        
        message += f"[TIME] Duration: {time_str}\n"
    
    # Settings
    compression_level = stats.get('compression_level', 'unknown')
    message += f"[COMPRESS] Level: {compression_level}\n"
    
    # Folders
    if stats.get('source_folder'):
        message += f"[FOLDER] Source: {stats['source_folder']}\n"
    if stats.get('target_folder'):
        message += f"[FOLDER] Target: {stats['target_folder']}\n"
    
    message += "\n"
    
    # File details (only if few files)
    files = stats.get('files', [])
    if files and len(files) <= 5:
        message += f"[FILE] Files processed:\n"
        for file_info in files:
            if isinstance(file_info, dict):
                name = file_info.get('name', 'unknown')
                percent = file_info.get('percent_saved', 0)
                message += f"• {name}: {percent:.1f}%\n"
        message += "\n"
    elif len(files) > 5:
        message += f"[FILE] Processed {len(files)} files\n\n"
    
    # Errors (first 3)
    errors = stats.get('errors', [])
    if errors:
        message += f"[ERROR] Errors ({len(errors)}):\n"
        for error in errors[:3]:
            if isinstance(error, dict):
                file_name = error.get('file', 'unknown')
                error_msg = error.get('error', 'unknown')
                # Truncate long error messages
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
    
    # Timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    message += f"[TIMESTAMP] {timestamp}"
    
    return message


def main():
    """Main function"""
    
    try:
        # Check arguments
        if len(sys.argv) < 2:
            print("Usage: python send_notification.py <report_file> [stats_file]")
            sys.exit(1)
        
        report_file = sys.argv[1]
        stats_file = sys.argv[2] if len(sys.argv) > 2 else 'temp/logs/stats.json'
        
        # Check token availability
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("[INFO] Telegram credentials not configured, skipping notification")
            sys.exit(0)
        
        # Load statistics
        stats = load_stats(stats_file)

        # Skip Telegram if no files were found/processed
        if stats and stats.get('processed_files', 0) == 0 and stats.get('failed_files', 0) == 0:
            print("[INFO] No files found. Skipping Telegram notification.")
            sys.exit(0)

        # Load report if needed
        report_content = ""
        if Path(report_file).exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = f.read()

        # Create notifier
        notifier = TelegramNotifier()

        # Send main message
        message = create_telegram_message(report_content, stats)

        print("[TELEGRAM] Sending Telegram notification...")
        success = notifier.send_message(message)

        if success:
            print("[SUCCESS] Telegram notification sent successfully")

            # Send detailed report as document if it exists and is large
            if Path(report_file).exists() and len(report_content) > 2000:
                print("[ATTACH] Sending detailed report as document...")
                doc_success = notifier.send_document(
                    report_file,
                    "[FILE] Detailed compression report"
                )
                if doc_success:
                    print("[SUCCESS] Detailed report sent successfully")
                else:
                    print("[WARNING] Failed to send detailed report")
        else:
            print("[ERROR] Failed to send Telegram notification")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Error sending notification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()