#!/usr/bin/env python3
"""
Простой отладочный скрипт для проверки конфигурации
"""

import sys
import os
from pathlib import Path
import yaml

def debug_config():
    """Отладка конфигурации"""
    
    print("=" * 60)
    print("🔍 ОТЛАДКА КОНФИГУРАЦИИ")
    print("=" * 60)
    
    # Проверяем переменные окружения
    print("\n🔐 Переменные окружения:")
    print(f"   MEGA_EMAIL: {'✅ SET' if os.getenv('MEGA_EMAIL') else '❌ NOT SET'}")
    print(f"   MEGA_PASSWORD: {'✅ SET' if os.getenv('MEGA_PASSWORD') else '❌ NOT SET'}")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ SET' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ NOT SET'}")
    print(f"   TELEGRAM_CHAT_ID: {'✅ SET' if os.getenv('TELEGRAM_CHAT_ID') else '❌ NOT SET'}")
    
    # Проверяем конфигурационный файл
    config_path = Path("config/settings.yaml")
    print(f"\n📋 Конфигурационный файл:")
    print(f"   Путь: {config_path}")
    print(f"   Существует: {'✅ YES' if config_path.exists() else '❌ NO'}")
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"\n📁 Папки:")
            folders = config.get('folders', {})
            print(f"   Input: {folders.get('input', 'NOT SET')}")
            print(f"   Output: {folders.get('output', 'NOT SET')}")
            print(f"   Backup: {folders.get('backup', 'NOT SET')}")
            
            print(f"\n🗜️ Сжатие:")
            compression = config.get('compression', {})
            print(f"   Default level: {compression.get('default_level', 'NOT SET')}")
            print(f"   Available levels: {list(compression.get('levels', {}).keys())}")
            
            print(f"\n📊 Лимиты:")
            limits = config.get('limits', {})
            print(f"   Max files per run: {limits.get('max_files_per_run', 'NOT SET')}")
            print(f"   Max file size (MB): {limits.get('max_file_size_mb', 'NOT SET')}")
            print(f"   Min file size (KB): {limits.get('min_file_size_kb', 'NOT SET')}")
            
            print(f"\n🔍 Фильтры:")
            filters = config.get('filters', {})
            print(f"   Skip patterns: {filters.get('skip_patterns', [])}")
            print(f"   Min compression %: {filters.get('min_compression_percent', 'NOT SET')}")
            
            print(f"\n📱 Уведомления:")
            notifications = config.get('notifications', {})
            telegram = notifications.get('telegram', {})
            print(f"   Telegram enabled: {telegram.get('enabled', False)}")
            
            print(f"\n🛡️ Безопасность:")
            safety = config.get('safety', {})
            print(f"   Create backup: {safety.get('create_backup', False)}")
            print(f"   Verify compression: {safety.get('verify_compression', False)}")
            print(f"   Rollback on error: {safety.get('rollback_on_error', False)}")
            
        except Exception as e:
            print(f"   ❌ Ошибка чтения конфигурации: {e}")
    
    # Проверяем .env файл
    print(f"\n📄 .env файл:")
    env_path = Path(".env")
    print(f"   Существует: {'✅ YES' if env_path.exists() else '❌ NO'}")
    
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"   Строк: {len(lines)}")
            for line in lines:
                if '=' in line:
                    key = line.split('=')[0].strip()
                    print(f"   - {key}")
        except Exception as e:
            print(f"   ❌ Ошибка чтения .env: {e}")
    
    # Проверяем структуру проекта
    print(f"\n📂 Структура проекта:")
    required_files = [
        'src/main.py',
        'src/compressor.py',
        'src/mega_client.py',
        'src/config.py',
        'src/utils.py',
        'config/settings.yaml',
        'requirements.txt'
    ]
    
    for file_path in required_files:
        exists = Path(file_path).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {file_path}")
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(debug_config())

