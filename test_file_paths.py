#!/usr/bin/env python3
"""
Детальный тест путей файлов в Mega
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("=" * 70)
print("🔍 ДЕТАЛЬНЫЙ ТЕСТ ПУТЕЙ ФАЙЛОВ")
print("=" * 70)

try:
    from mega import Mega
    
    mega = Mega()
    email = os.getenv('MEGA_EMAIL')
    password = os.getenv('MEGA_PASSWORD')
    
    print(f"\n🔐 Вход в Mega...")
    m = mega.login(email, password)
    print("✅ Успешно вошли")
    
    # Получаем все файлы
    print("\n📂 Получение всех файлов...")
    files = m.get_files()
    print(f"   Всего объектов: {len(files)}")
    
    # Показываем детальную информацию о каждом файле
    print("\n📊 Детальная информация о файлах:")
    for file_id, file_info in files.items():
        if not isinstance(file_info, dict):
            continue
        
        name = file_info.get('a', {}).get('n', '?') if 'a' in file_info else '?'
        file_type = file_info.get('t', '?')
        parent_id = file_info.get('p', '?')
        type_str = "📁 ПАПКА" if file_type == 1 else "📄 ФАЙЛ"
        
        print(f"\n   {type_str}: {name}")
        print(f"      ID: {file_id}")
        print(f"      Parent ID: {parent_id}")
        print(f"      Type: {file_type}")
        
        # Если это PDF файл, показываем полный путь
        if name.lower().endswith('.pdf'):
            print(f"      ⭐ ЭТО PDF ФАЙЛ!")
            
            # Строим путь
            path_parts = []
            current_id = file_id
            
            print(f"      Построение пути:")
            while current_id in files:
                current_file = files[current_id]
                if 'a' not in current_file:
                    print(f"         └─ Нет 'a' в файле {current_id}")
                    break
                
                current_name = current_file['a'].get('n', '')
                if current_name:
                    path_parts.insert(0, current_name)
                    print(f"         ├─ {current_name} (ID: {current_id})")
                
                parent_id = current_file.get('p')
                if not parent_id:
                    print(f"         └─ Нет parent_id")
                    break
                
                current_id = parent_id
            
            full_path = '/' + '/'.join(path_parts) if path_parts else ''
            print(f"      Полный путь: {full_path}")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

