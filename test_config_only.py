#!/usr/bin/env python3
"""
Тест конфигурации без скачивания файлов
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import get_config
from mega_client import MegaClient

print("=" * 70)
print("📋 ТЕСТ КОНФИГУРАЦИИ PDF КОМПРЕССОРА")
print("=" * 70)

try:
    # 1. Загружаем конфигурацию
    print("\n1️⃣ Загрузка конфигурации...")
    config = get_config()
    print("   ✅ Конфигурация загружена")
    
    # 2. Выводим основные параметры
    print("\n2️⃣ Параметры конфигурации:")
    print(f"   📁 Входная папка: {config.input_folder}")
    print(f"   📁 Выходная папка: {config.output_folder}")
    print(f"   📁 Папка бэкапа: {config.backup_folder}")
    print(f"   🗜️  Уровень сжатия: {config.default_compression_level}")
    print(f"   📊 Макс. файлов: {config.max_files_per_run}")
    print(f"   💾 Макс. размер: {config.max_file_size_mb} MB")
    
    # 3. Проверяем учетные данные
    print("\n3️⃣ Проверка учетных данных:")
    if config.mega_email:
        print(f"   ✅ Email: {config.mega_email}")
    else:
        print("   ❌ Email не установлен")
    
    if config.mega_password:
        print(f"   ✅ Пароль: {'*' * len(config.mega_password)}")
    else:
        print("   ❌ Пароль не установлен")
    
    # 4. Валидация конфигурации
    print("\n4️⃣ Валидация конфигурации:")
    validation = config.validate()
    
    if validation['errors']:
        print(f"   ❌ Ошибки ({len(validation['errors'])}):")
        for error in validation['errors']:
            print(f"      • {error}")
    else:
        print("   ✅ Ошибок не найдено")
    
    if validation['warnings']:
        print(f"   ⚠️  Предупреждения ({len(validation['warnings'])}):")
        for warning in validation['warnings']:
            print(f"      • {warning}")
    else:
        print("   ✅ Предупреждений не найдено")
    
    # 5. Проверяем подключение к Mega
    print("\n5️⃣ Проверка подключения к Mega...")
    try:
        mega_client = MegaClient()
        print("   ✅ Подключение успешно!")
        
        # Получаем информацию о квоте
        try:
            quota = mega_client.get_quota()
            print(f"   📊 Квота: {quota}")
        except Exception as e:
            print(f"   ⚠️  Не удалось получить квоту: {e}")
        
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        sys.exit(1)
    
    # 6. Итоговый результат
    print("\n" + "=" * 70)
    if not validation['errors']:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Программа готова к работе.")
    else:
        print("❌ ЕСТЬ ОШИБКИ! Исправьте их перед запуском.")
        sys.exit(1)
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

