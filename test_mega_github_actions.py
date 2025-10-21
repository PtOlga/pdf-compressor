#!/usr/bin/env python3
"""
Тест подключения к Mega на GitHub Actions
"""

import os
import sys
import time
import json

# Добавляем src в path
sys.path.insert(0, 'src')

print("=" * 70)
print("🧪 Тест подключения к Mega на GitHub Actions")
print("=" * 70)

# Проверяем переменные окружения
print("\n📋 Проверка переменных окружения:")
mega_email = os.getenv('MEGA_EMAIL')
mega_password = os.getenv('MEGA_PASSWORD')

print(f"   MEGA_EMAIL: {'✅ установлена' if mega_email else '❌ не установлена'}")
print(f"   MEGA_PASSWORD: {'✅ установлена' if mega_password else '❌ не установлена'}")

if not mega_email or not mega_password:
    print("\n❌ Ошибка: Не установлены переменные окружения MEGA_EMAIL и MEGA_PASSWORD")
    sys.exit(1)

# Проверяем доступность API
print("\n🌐 Проверка доступности Mega API:")
try:
    import requests
    response = requests.get('https://g.api.mega.co.nz/cs', timeout=10)
    print(f"   Статус: {response.status_code}")
    print(f"   Размер ответа: {len(response.text)} байт")
    if response.text:
        print(f"   Ответ: {response.text[:100]}")
    else:
        print("   ⚠️ Пустой ответ от API!")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Патч для mega.py - добавляем User-Agent
print("\n🔧 Применяю патч для mega.py...")
try:
    import requests
    original_post = requests.post

    def patched_post(*args, **kwargs):
        """Патч для добавления User-Agent к запросам"""
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'User-Agent' not in kwargs['headers']:
            kwargs['headers']['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        return original_post(*args, **kwargs)

    requests.post = patched_post
    print("   ✅ Патч применен")
except Exception as e:
    print(f"   ⚠️ Не удалось применить патч: {e}")

# Пытаемся подключиться к Mega
print("\n🔐 Попытка подключения к Mega:")
try:
    from mega import Mega
    
    print("   ✅ Библиотека mega.py импортирована")
    
    mega = Mega()
    print("   ✅ Объект Mega создан")
    
    print(f"   ⏳ Попытка входа с email: {mega_email}")
    
    # Пытаемся войти с повторными попытками
    for attempt in range(3):
        try:
            print(f"      Попытка {attempt + 1}/3...")
            m = mega.login(mega_email, mega_password)
            print("      ✅ Успешно вошли в Mega!")
            
            # Получаем информацию о квоте
            print("\n💾 Информация о квоте:")
            try:
                quota = m.get_quota()
                print(f"   ✅ Квота получена: {json.dumps(quota, indent=2)}")
            except Exception as e:
                print(f"   ⚠️ Не удалось получить квоту: {e}")
            
            # Получаем список файлов
            print("\n📂 Получение списка файлов:")
            try:
                files = m.get_files()
                print(f"   ✅ Получено {len(files)} объектов")
            except Exception as e:
                print(f"   ⚠️ Не удалось получить список файлов: {e}")
            
            break
            
        except Exception as e:
            print(f"      ❌ Ошибка: {type(e).__name__}: {e}")
            if attempt < 2:
                wait_time = 5 * (attempt + 1)
                print(f"      ⏳ Жду {wait_time} сек перед следующей попыткой...")
                time.sleep(wait_time)
            else:
                raise
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ Тест завершен успешно!")
print("=" * 70)

