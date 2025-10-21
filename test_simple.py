#!/usr/bin/env python3
"""
Простой тест подключения к Mega и поиска файлов
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("=" * 70)
print("🔍 ПРОСТОЙ ТЕСТ MEGA")
print("=" * 70)

# Проверяем учетные данные
email = os.getenv('MEGA_EMAIL')
password = os.getenv('MEGA_PASSWORD')

print(f"\n🔐 Учетные данные:")
print(f"   Email: {email if email else '❌ NOT SET'}")
print(f"   Password: {'✅ SET' if password else '❌ NOT SET'}")

if not email or not password:
    print("\n❌ ОШИБКА: Не установлены MEGA_EMAIL и MEGA_PASSWORD")
    sys.exit(1)

print("\n⏳ Подключение к Mega...")

try:
    from mega_client import MegaClient
    
    mega_client = MegaClient()
    print("✅ Успешно подключено к Mega!")
    
    # Получаем список файлов
    print("\n🔎 Поиск PDF файлов в /PDF/Input...")
    pdf_files = mega_client.list_pdf_files("/PDF/Input")
    
    print(f"\n✅ Найдено {len(pdf_files)} PDF файлов:")
    for f in pdf_files:
        print(f"   📄 {f['name']} ({f['size']} bytes)")
    
    if not pdf_files:
        print("\n⚠️ PDF файлы не найдены!")
        print("\n🔍 Проверяем структуру Mega...")
        
        # Получаем все файлы для диагностики
        files = mega_client.mega.get_files()
        print(f"   Всего объектов: {len(files)}")
        
        # Показываем первые 20 объектов
        print("\n   Первые 20 объектов:")
        count = 0
        for file_id, file_info in files.items():
            if count >= 20:
                break
            
            if not isinstance(file_info, dict) or 'a' not in file_info:
                continue
            
            name = file_info['a'].get('n', '?')
            file_type = file_info.get('t', '?')
            type_str = "ПАПКА" if file_type == 1 else "ФАЙЛ"
            
            print(f"      {type_str}: {name}")
            count += 1

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)

