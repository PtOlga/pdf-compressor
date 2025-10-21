#!/usr/bin/env python3
"""
Тест подключения к Mega API
"""

import os
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения
load_dotenv()

print("=" * 70)
print("🔍 ТЕСТ MEGA API")
print("=" * 70)

email = os.getenv('MEGA_EMAIL')
password = os.getenv('MEGA_PASSWORD')

print(f"\n🔐 Учетные данные:")
print(f"   Email: {email}")
print(f"   Password: {password}")

if not email or not password:
    print("\n❌ ОШИБКА: Не установлены MEGA_EMAIL и MEGA_PASSWORD")
    exit(1)

# Проверяем интернет
print("\n🌐 Проверка подключения к интернету...")
try:
    response = requests.get('https://www.google.com', timeout=5)
    print(f"   ✅ Интернет доступен (статус: {response.status_code})")
except Exception as e:
    print(f"   ❌ Нет интернета: {e}")
    exit(1)

# Проверяем доступность Mega API
print("\n🔗 Проверка доступности Mega API...")
try:
    response = requests.post('https://g.api.mega.co.nz/cs', json={'a': 'us'}, timeout=10)
    print(f"   ✅ Mega API доступен (статус: {response.status_code})")
    print(f"   Ответ: {response.text[:100]}")
except Exception as e:
    print(f"   ❌ Mega API недоступен: {e}")
    exit(1)

# Пытаемся подключиться через mega.py
print("\n⏳ Попытка подключения через mega.py...")
try:
    from mega import Mega
    
    mega = Mega()
    print("   ✅ Объект Mega создан")
    
    print(f"   ⏳ Попытка входа с email: {email}")
    m = mega.login(email, password)
    print("   ✅ Успешно вошли в Mega!")
    
    # Получаем информацию о квоте
    print("\n💾 Информация о квоте:")
    try:
        quota = m.get_quota()
        print(f"   ✅ Квота получена: {quota}")
    except Exception as e:
        print(f"   ⚠️ Не удалось получить квоту: {e}")
    
    # Получаем список файлов
    print("\n📂 Получение списка файлов...")
    files = m.get_files()
    print(f"   ✅ Получено {len(files)} объектов")
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

