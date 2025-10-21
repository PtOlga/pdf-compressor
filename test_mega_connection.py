#!/usr/bin/env python3
"""
Тест подключения к Mega и поиска файлов
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

print("=" * 70)
print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К MEGA")
print("=" * 70)

# Проверяем учетные данные
email = os.getenv('MEGA_EMAIL')
password = os.getenv('MEGA_PASSWORD')

print(f"\n🔐 Учетные данные:")
print(f"   Email: {email if email else '❌ NOT SET'}")
print(f"   Password: {'✅ SET' if password else '❌ NOT SET'}")

if not email or not password:
    print("\n❌ ОШИБКА: Не установлены MEGA_EMAIL и MEGA_PASSWORD")
    print("   Установите их в .env файле или переменных окружения")
    exit(1)

print("\n⏳ Подключение к Mega...")

try:
    from mega import Mega
    
    mega = Mega()
    m = mega.login(email, password)
    
    print("✅ Успешно подключено к Mega!")
    
    # Получаем информацию о квоте
    print("\n💾 Информация о квоте:")
    try:
        quota = m.get_quota()
        total = quota.get('total', 0)
        used = quota.get('used', 0)
        free = total - used
        
        def format_size(b):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if b < 1024:
                    return f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} TB"
        
        print(f"   Всего: {format_size(total)}")
        print(f"   Использовано: {format_size(used)}")
        print(f"   Свободно: {format_size(free)}")
    except Exception as e:
        print(f"   ⚠️ Не удалось получить квоту: {e}")
    
    # Получаем все файлы
    print("\n📂 Получение списка файлов...")
    files = m.get_files()
    
    print(f"   Всего объектов: {len(files)}")
    
    # Анализируем структуру
    print("\n📋 Структура файлов (первые 30):")
    print(f"{'ID':<20} {'Тип':<8} {'Имя':<30} {'Размер':<12}")
    print("-" * 70)
    
    count = 0
    for file_id, file_info in files.items():
        if count >= 30:
            break
        
        if not isinstance(file_info, dict):
            continue
        
        if 'a' not in file_info:
            continue
        
        name = file_info['a'].get('n', '?')
        file_type = file_info.get('t', '?')
        size = file_info.get('s', 0)
        
        type_str = "ПАПКА" if file_type == 1 else "ФАЙЛ" if file_type == 0 else f"ТИП{file_type}"
        
        size_str = format_size(size) if size > 0 else "-"
        
        print(f"{file_id:<20} {type_str:<8} {name:<30} {size_str:<12}")
        count += 1
    
    if len(files) > 30:
        print(f"... и еще {len(files) - 30} объектов")
    
    # Ищем папку /PDF/Input
    print("\n🔎 Поиск папки /PDF/Input...")
    
    def get_file_path(file_id, all_files):
        """Получение полного пути к файлу"""
        try:
            path_parts = []
            current_id = file_id
            
            while current_id in all_files:
                file_info = all_files[current_id]
                if 'a' not in file_info:
                    break
                
                name = file_info['a'].get('n', '')
                if name:
                    path_parts.insert(0, name)
                
                parent_id = file_info.get('p')
                if not parent_id:
                    break
                    
                current_id = parent_id
            
            if path_parts:
                return '/' + '/'.join(path_parts)
            else:
                return ''
        except Exception:
            return ''
    
    input_folder = "/PDF/Input"
    found_files = []
    
    for file_id, file_info in files.items():
        if not isinstance(file_info, dict) or 'a' not in file_info:
            continue
        
        name = file_info['a'].get('n', '')
        file_path = get_file_path(file_id, files)
        size = file_info.get('s', 0)
        file_type = file_info.get('t', 0)
        
        # Проверяем, находится ли файл в целевой папке
        if file_path and file_path.startswith(input_folder.rstrip('/')):
            if name.lower().endswith(('.pdf', '.PDF')):
                found_files.append({
                    'name': name,
                    'path': file_path,
                    'size': size,
                    'id': file_id
                })
    
    if found_files:
        print(f"✅ Найдено {len(found_files)} PDF файлов:")
        for f in found_files:
            print(f"   📄 {f['name']}")
            print(f"      Путь: {f['path']}")
            print(f"      Размер: {format_size(f['size'])}")
            print(f"      ID: {f['id']}")
    else:
        print(f"❌ PDF файлы не найдены в {input_folder}")
        
        # Проверяем, существует ли сама папка
        print(f"\n🔍 Проверка существования папки {input_folder}...")
        
        folder_exists = False
        for file_id, file_info in files.items():
            if not isinstance(file_info, dict) or 'a' not in file_info:
                continue
            
            file_path = get_file_path(file_id, files)
            file_type = file_info.get('t', 0)
            
            if file_path == input_folder and file_type == 1:
                print(f"✅ Папка найдена!")
                folder_exists = True
                break
        
        if not folder_exists:
            print(f"❌ Папка {input_folder} не найдена!")
            print(f"\n💡 Доступные папки:")
            
            folders = []
            for file_id, file_info in files.items():
                if not isinstance(file_info, dict) or 'a' not in file_info:
                    continue
                
                file_type = file_info.get('t', 0)
                if file_type == 1:  # Папка
                    file_path = get_file_path(file_id, files)
                    if file_path:
                        folders.append(file_path)
            
            folders.sort()
            for folder in folders[:20]:
                print(f"   📁 {folder}")
            
            if len(folders) > 20:
                print(f"   ... и еще {len(folders) - 20} папок")

except ImportError:
    print("❌ Библиотека mega.py не установлена")
    print("   Установите: pip install mega.py")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

