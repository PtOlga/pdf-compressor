#!/usr/bin/env python3
"""
Тест поиска PDF файлов в Mega
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
print("🔍 ТЕСТ ПОИСКА PDF ФАЙЛОВ")
print("=" * 70)

try:
    from mega_client import MegaClient
    
    mega_client = MegaClient()
    print("✅ Подключено к Mega")
    
    # Получаем все файлы
    print("\n📂 Получение всех объектов из Mega...")
    files = mega_client.mega.get_files()
    print(f"   Всего объектов: {len(files)}")
    
    # Показываем структуру
    print("\n📊 Структура Mega:")
    for file_id, file_info in files.items():
        if not isinstance(file_info, dict) or 'a' not in file_info:
            continue
        
        name = file_info['a'].get('n', '?')
        file_type = file_info.get('t', '?')
        type_str = "📁" if file_type == 1 else "📄"
        
        print(f"   {type_str} {name}")
    
    # Пытаемся найти файлы в разных путях
    print("\n🔎 Поиск PDF файлов в разных путях:")
    
    paths_to_try = [
        "/Cloud Drive/pdf/Input",
        "/pdf/Input",
        "/PDF/Input",
        "/Input",
        "/pdf",
        "/PDF",
    ]
    
    for path in paths_to_try:
        print(f"\n   🔍 Путь: {path}")
        try:
            pdf_files = mega_client.list_pdf_files(path)
            print(f"      ✅ Найдено {len(pdf_files)} PDF файлов")
            for f in pdf_files:
                print(f"         📄 {f['name']} ({f['size']} bytes)")
        except Exception as e:
            print(f"      ❌ Ошибка: {e}")
    
    # Проверяем метод get_folder_info
    print("\n📊 Информация о папке /Cloud Drive/pdf/Input:")
    try:
        folder_info = mega_client.get_folder_info("/Cloud Drive/pdf/Input")
        print(f"   Всего файлов: {folder_info['total_files']}")
        print(f"   Всего размер: {folder_info['total_size']} bytes")
        print(f"   Файлы:")
        for f in folder_info['files']:
            print(f"      📄 {f['name']} ({f['size']} bytes)")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

